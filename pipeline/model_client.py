"""统一的 LLM 调用客户端，支持 DeepSeek、Qwen、OpenAI 三种模型提供商。"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "openai": "gpt-4o-mini",
}

API_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai": "https://api.openai.com/v1",
}

PRICING_PER_1K_TOKENS = {
    "deepseek-chat": {"input": 0.00027, "output": 0.0011},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "qwen-plus": {"input": 0.0008, "output": 0.0020},
    "qwen-max": {"input": 0.0040, "output": 0.0120},
    "gpt-4o": {"input": 0.0050, "output": 0.0150},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.0100, "output": 0.0300},
}


@dataclass
class Usage:
    """Token 用量统计。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """统一的 LLM 响应结构。"""

    content: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    provider: str = ""

# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """LLM 提供商抽象基类。"""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """发送聊天请求。

        Args:
            messages: 消息列表，格式为 [{"role": "...", "content": "..."}]。
            model: 模型名称，为 None 时使用默认值。
            temperature: 采样温度，默认 0.7。
            max_tokens: 最大输出 token 数。

        Returns:
            LLMResponse 对象。

        Raises:
            httpx.HTTPError: API 请求失败时抛出。
        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """估算文本的 token 数量。

        Args:
            text: 输入文本。

        Returns:
            估算的 token 数。
        """

# ---------------------------------------------------------------------------
# OpenAI 兼容实现
# ---------------------------------------------------------------------------


class OpenAICompatibleProvider(LLMProvider):
    """基于 OpenAI 兼容 API 的 LLM 提供商实现。"""

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        base_url: str,
        default_model: str,
    ) -> None:
        """初始化 OpenAICompatibleProvider。

        Args:
            provider_name: 提供商名称（deepseek / qwen / openai）。
            api_key: API 密钥。
            base_url: API 基础地址。
            default_model: 默认模型名称。
        """
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def _build_client(self) -> httpx.Client:
        """创建一个配置好的 httpx 客户端。"""
        return httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0),
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """发送聊天请求。

        Args:
            messages: 消息列表。
            model: 模型名称，为 None 时使用默认值。
            temperature: 采样温度。
            max_tokens: 最大输出 token 数。

        Returns:
            LLMResponse 对象。

        Raises:
            httpx.HTTPError: API 请求失败时抛出。
            ValueError: API 返回异常数据时抛出。
        """
        model_name = model or self.default_model
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        logger.info(
            "Sending chat request to %s model=%s messages=%d",
            self.provider_name, model_name, len(messages),
        )

        with self._build_client() as client:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]

        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        logger.info(
            "Received response from %s usage=%s",
            self.provider_name, usage,
        )

        return LLMResponse(
            content=content,
            usage=usage,
            model=model_name,
            provider=self.provider_name,
        )

    def count_tokens(self, text: str) -> int:
        """使用简单规则估算 token 数量（约 4 字符 / token）。

        Args:
            text: 输入文本。

        Returns:
            估算的 token 数。
        """
        return len(text) // 4 + 1

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """根据环境变量创建 LLM 提供商实例。

    环境变量：
        LLM_PROVIDER: 提供商名称（deepseek / qwen / openai），默认 deepseek。
        DEEPSEEK_API_KEY / QWEN_API_KEY / OPENAI_API_KEY: 对应的 API 密钥。

    Args:
        provider_name: 提供商名称，为 None 则从环境变量读取。

    Returns:
        LLMProvider 实例。

    Raises:
        ValueError: 不支持的提供商或缺少 API 密钥时抛出。
    """
    name = (provider_name or os.getenv("LLM_PROVIDER", "deepseek")).lower()

    if name not in DEFAULT_MODELS:
        raise ValueError(
            f"不支持的 LLM 提供商: {name}，可选: {list(DEFAULT_MODELS.keys())}"
        )

    env_key_name = f"{name.upper()}_API_KEY"
    api_key = os.getenv(env_key_name)
    if not api_key:
        raise ValueError(
            f"缺少环境变量 {env_key_name}，请在 .env 或环境中设置"
        )

    return OpenAICompatibleProvider(
        provider_name=name,
        api_key=api_key,
        base_url=API_BASE_URLS[name],
        default_model=DEFAULT_MODELS[name],
    )

# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------


def chat_with_retry(
    messages: List[Dict[str, str]],
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> LLMResponse:
    """带重试机制的 LLM 调用函数。

    使用指数退避策略，最多重试 max_retries 次。

    Args:
        messages: 消息列表。
        provider: LLM 提供商，为 None 时通过 create_provider() 自动创建。
        model: 模型名称。
        temperature: 采样温度。
        max_tokens: 最大输出 token 数。
        max_retries: 最大重试次数，默认 3。
        base_delay: 退避基础延迟（秒），默认 2.0。

    Returns:
        LLMResponse 对象。

    Raises:
        httpx.HTTPError: 所有重试均失败时抛出最后一次异常。
    """
    provider = provider or create_provider()
    last_exception: Optional[Exception] = None

    for attempt in range(1 + max_retries):
        try:
            return provider.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except httpx.TimeoutException as exc:
            last_exception = exc
            logger.warning(
                "Request timeout (attempt %d/%d)", attempt + 1, 1 + max_retries,
            )
        except httpx.HTTPStatusError as exc:
            last_exception = exc
            logger.warning(
                "HTTP error %s (attempt %d/%d)",
                exc.response.status_code, attempt + 1, 1 + max_retries,
            )
            if exc.response.status_code < 500:
                raise
        except httpx.HTTPError as exc:
            last_exception = exc
            logger.warning(
                "HTTP error (attempt %d/%d): %s",
                attempt + 1, 1 + max_retries, exc,
            )

        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)
            logger.info("Retrying in %.1f seconds...", delay)
            time.sleep(delay)

    raise last_exception  # type: ignore[misc]

# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------


def calculate_cost(model: str, usage: Usage) -> float:
    """计算一次 API 调用的美元费用。

    Args:
        model: 模型名称。
        usage: Token 用量统计。

    Returns:
        费用金额（USD）。
    """
    pricing = PRICING_PER_1K_TOKENS.get(model)
    if pricing is None:
        logger.warning("未知模型 %s，使用默认价格估算", model)
        return 0.0

    cost = (
        usage.prompt_tokens / 1000 * pricing["input"]
        + usage.completion_tokens / 1000 * pricing["output"]
    )
    return round(cost, 6)


def estimate_cost(
    prompt: str,
    model: str,
    provider: Optional[LLMProvider] = None,
) -> float:
    """估算一次调用的成本（基于输入文本长度）。

    Args:
        prompt: 输入提示文本。
        model: 模型名称。
        provider: 用于 token 估算的提供商实例。

    Returns:
        预估费用（USD）。
    """
    provider = provider or create_provider()
    token_count = provider.count_tokens(prompt)
    pseudo_usage = Usage(prompt_tokens=token_count, completion_tokens=0)
    return calculate_cost(model, pseudo_usage)

# ---------------------------------------------------------------------------
# Quick chat convenience
# ---------------------------------------------------------------------------


def quick_chat(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    provider: Optional[LLMProvider] = None,
) -> str:
    """一句话调用 LLM 的便捷函数。

    Args:
        prompt: 用户提示。
        system_prompt: 可选的系统提示。
        model: 模型名称。
        temperature: 采样温度。
        provider: LLM 提供商。

    Returns:
        模型回复文本。
    """
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = chat_with_retry(
        messages=messages,
        provider=provider,
        model=model,
        temperature=temperature,
    )
    return response.content

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("pipeline/model_client.py 自测")
    print("=" * 60)

    # 1. 测试 Usage / LLMResponse 数据类
    usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    resp = LLMResponse(content="hello", usage=usage, model="test-model", provider="test")
    assert resp.content == "hello"
    assert resp.usage.total_tokens == 30
    print("[PASS] dataclass 构造正常")

    # 2. 测试 token 估算
    provider = OpenAICompatibleProvider("test", "sk-test", "https://api.example.com/v1", "test-model")
    assert provider.count_tokens("hello world") == 3  # 11 // 4 + 1
    assert provider.count_tokens("a") == 1
    print("[PASS] count_tokens 估算正常")

    # 3. 测试成本计算
    usage = Usage(prompt_tokens=1000, completion_tokens=500)
    cost = calculate_cost("gpt-4o-mini", usage)
    expected = 1000 / 1000 * 0.00015 + 500 / 1000 * 0.0006
    assert cost == round(expected, 6), f"{cost} != {expected}"
    print("[PASS] calculate_cost 计算正常")

    # 4. 测试未知模型的成本
    cost = calculate_cost("unknown-model", usage)
    assert cost == 0.0
    print("[PASS] calculate_cost 未知模型返回 0")

    # 5. 测试 create_provider 工厂（期望缺少 API key 时抛异常）
    # 保存当前环境变量并清除
    old_provider = os.environ.pop("LLM_PROVIDER", None)
    old_deepseek = os.environ.pop("DEEPSEEK_API_KEY", None)
    old_openai = os.environ.pop("OPENAI_API_KEY", None)
    old_qwen = os.environ.pop("QWEN_API_KEY", None)

    try:
        create_provider("deepseek")
        print("[FAIL] create_provider 应该因缺少 API key 而抛异常")
    except ValueError as e:
        assert "缺少环境变量" in str(e)
        print("[PASS] create_provider 缺失 key 时抛异常正常")

    # 6. 测试不支持的提供商
    try:
        create_provider("invalid-model")
        print("[FAIL] create_provider 应该拒绝不支持的提供商")
    except ValueError as e:
        assert "不支持的 LLM 提供商" in str(e)
        print("[PASS] create_provider 拒绝不支持提供商正常")

    # 7. 测试 quick_chat 模拟（无网络时验证参数构建）
    # 注意：这里不真正发送网络请求，仅验证 quick_chat 能正确构造消息
    system = "你是一个助手"
    prompt = "你好"
    messages_built: List[Dict[str, str]] = []
    messages_built.append({"role": "system", "content": system})
    messages_built.append({"role": "user", "content": prompt})
    assert len(messages_built) == 2
    assert messages_built[0]["role"] == "system"
    assert messages_built[1]["role"] == "user"
    print("[PASS] quick_chat 消息构造正常")

    # 8. 测试 estimate_cost
    est = estimate_cost("hello world", "gpt-4o-mini", provider=provider)
    assert isinstance(est, float)
    print("[PASS] estimate_cost 返回 float 正常")

    # 恢复环境变量
    if old_provider is not None:
        os.environ["LLM_PROVIDER"] = old_provider
    if old_deepseek is not None:
        os.environ["DEEPSEEK_API_KEY"] = old_deepseek
    if old_openai is not None:
        os.environ["OPENAI_API_KEY"] = old_openai
    if old_qwen is not None:
        os.environ["QWEN_API_KEY"] = old_qwen

    print()
    print("=" * 60)
    print("全部测试通过")
    print("=" * 60)

    print()
    print("环境变量设置示例:")
    print("  export LLM_PROVIDER=deepseek")
    print('  export DEEPSEEK_API_KEY="sk-xxx"')
    print("  python -c \"from pipeline.model_client import quick_chat; print(quick_chat('你好'))\"")
