"""四步知识库自动化流水线：采集 → 分析 → 整理 → 保存。"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import httpx
import yaml

from model_client import LLMResponse, create_provider, chat_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
RAW_DIR = BASE_DIR / "knowledge" / "raw"
ARTICLES_DIR = BASE_DIR / "knowledge" / "articles"
RSS_CONFIG = BASE_DIR / "pipeline" / "rss_sources.yaml"

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

DATE_STAMP = datetime.now(timezone.utc).strftime("%Y%m%d")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class RawItem:
    """采集到的原始数据条目。"""

    def __init__(
        self,
        title: str,
        url: str,
        source: str,
        summary: str = "",
        popularity: int = 0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.title = title
        self.url = url
        self.source = source
        self.summary = summary
        self.popularity = popularity
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "popularity": self.popularity,
            **self.extra,
        }


class Article:
    """结构化知识条目，对应 knowledge/articles/ 下的 JSON 文件。"""

    REQUIRED_FIELDS = {"id", "title", "source_url", "source_platform",
                       "summary", "tags", "status", "created_at",
                       "updated_at", "analysis"}
    ANALYSIS_FIELDS = {"description", "tech_category", "innovation",
                       "difficulty", "use_cases", "score"}

    def __init__(self, raw: RawItem, analysis: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        slug = _slugify(raw.title)
        self.data: Dict[str, Any] = {
            "id": f"{slug}-{DATE_STAMP}",
            "title": raw.title,
            "source_url": raw.url,
            "source_platform": raw.source,
            "summary": analysis.get("summary", raw.summary),
            "tags": analysis.get("tags", []),
            "status": "analyzed",
            "created_at": now,
            "updated_at": now,
            "analysis": {
                "description": analysis.get("description", ""),
                "tech_category": analysis.get("tech_category", ""),
                "innovation": analysis.get("innovation", ""),
                "difficulty": analysis.get("difficulty", ""),
                "use_cases": analysis.get("use_cases", []),
                "score": analysis.get("score", 0),
            },
        }

    @property
    def source_url(self) -> str:
        return self.data["source_url"]

    def validate(self) -> List[str]:
        """校验必填字段，返回缺失字段列表。"""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in self.data:
                missing.append(field)
        analysis = self.data.get("analysis", {})
        for field in self.ANALYSIS_FIELDS:
            if field not in analysis:
                missing.append(f"analysis.{field}")
        return missing

    def to_json(self, ensure_ascii: bool = False) -> str:
        return json.dumps(self.data, ensure_ascii=ensure_ascii, indent=2)

    @property
    def filename(self) -> str:
        return f"{DATE_STAMP}-{_slugify(self.data['title'])}.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """将文本转为短横线分隔的 slug。

    Args:
        text: 输入文本。

    Returns:
        小写字母数字短横线格式的 slug。
    """
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:64] or "untitled"


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rss_sources() -> List[Dict[str, Any]]:
    """从 YAML 配置文件加载已启用的 RSS 源列表。"""
    if not RSS_CONFIG.exists():
        logger.warning("RSS 配置文件不存在: %s", RSS_CONFIG)
        return []
    with open(RSS_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [s for s in config.get("sources", []) if s.get("enabled", False)]


# ---------------------------------------------------------------------------
# Step 1: Collect
# ---------------------------------------------------------------------------


def _collect_github(limit: int = 10) -> List[RawItem]:
    """从 GitHub Search API 采集 AI 相关热门仓库。

    搜索名称/描述中包含 AI、LLM、Agent 关键词且 stars 最多的仓库。

    Args:
        limit: 最多采集数量（1~100）。

    Returns:
        RawItem 列表。
    """
    query = "ai OR llm OR agent in:name,description,topics"
    params: Dict[str, Any] = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 100),
    }
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    logger.info("Fetching GitHub repos: q=%s per_page=%d", query, params["per_page"])

    try:
        with httpx.Client(headers=headers, timeout=30.0) as client:
            resp = client.get(GITHUB_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("GitHub API request failed: %s", exc)
        return []

    items: List[RawItem] = []
    for repo in data.get("items", [])[:limit]:
        items.append(RawItem(
            title=repo.get("full_name", repo.get("name", "unknown")),
            url=repo.get("html_url", ""),
            source="github",
            summary=repo.get("description") or "",
            popularity=repo.get("stargazers_count", 0),
            extra={
                "owner": repo.get("owner", {}).get("login", ""),
                "topics": repo.get("topics", []),
                "language": repo.get("language") or "",
                "forks": repo.get("forks_count", 0),
                "updated_at": repo.get("updated_at", ""),
            },
        ))

    logger.info("Collected %d items from GitHub", len(items))
    return items


def _collect_rss(limit: int = 10) -> List[RawItem]:
    """从 RSS 源采集 AI 相关内容。

    使用简易正则解析 RSS/Atom XML。

    Args:
        limit: 每个源最多采集数量。

    Returns:
        RawItem 列表。
    """
    sources = _load_rss_sources()
    if not sources:
        logger.info("No enabled RSS sources")
        return []

    items: List[RawItem] = []

    for source in sources:
        name = source["name"]
        url = source["url"]
        logger.info("Fetching RSS: %s (%s)", name, url)

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                raw_xml = resp.text
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch RSS %s: %s", name, exc)
            continue

        parsed = _parse_rss_xml(raw_xml, name)
        for entry in parsed[:limit]:
            items.append(RawItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                source="rss",
                summary=entry.get("description", ""),
                popularity=0,
                extra={"source_name": name},
            ))

    logger.info("Collected %d items from RSS", len(items))
    return items


def _parse_rss_xml(raw_xml: str, source_name: str) -> List[Dict[str, str]]:
    """用简易正则 + ElementTree 解析 RSS/Atom XML。

    Args:
        raw_xml: XML 原始文本。
        source_name: 源名称（仅用于日志）。

    Returns:
        条目字典列表，每项含 title/link/description。
    """
    entries: List[Dict[str, str]] = []

    title_pattern = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
    link_pattern = re.compile(r"<link[^>]*>(.*?)</link>", re.DOTALL | re.IGNORECASE)
    desc_pattern = re.compile(r"<description[^>]*>(.*?)</description>", re.DOTALL | re.IGNORECASE)

    items = re.findall(r"<item>(.*?)</item>", raw_xml, re.DOTALL | re.IGNORECASE)
    if not items:
        items = re.findall(r"<entry>(.*?)</entry>", raw_xml, re.DOTALL | re.IGNORECASE)

    for item_xml in items:
        title = _extract_tag(item_xml, title_pattern, "Untitled")
        link = _extract_tag(item_xml, link_pattern, "")
        desc = _extract_tag(item_xml, desc_pattern, "")

        desc = re.sub(r"<[^>]+>", "", desc)
        desc = desc.strip()[:500]

        entries.append({"title": title, "link": link, "description": desc})

    logger.debug("Parsed %d entries from %s", len(entries), source_name)
    return entries


def _extract_tag(xml: str, pattern: re.Pattern, default: str = "") -> str:
    """从 XML 片段中用正则提取标签内容。

    Args:
        xml: XML 片段。
        pattern: 编译好的正则表达式。
        default: 未匹配时的默认值。

    Returns:
        提取到的文本。
    """
    match = pattern.search(xml)
    if match:
        text = match.group(1).strip()
        text = text.replace("\\n", " ").replace("\\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text
    return default


def collect(sources: List[str], limit: int) -> List[RawItem]:
    """Step 1: 从指定源采集数据。

    Args:
        sources: 源名称列表，如 ["github", "rss"]。
        limit: 每个源的最大采集数量。

    Returns:
        合并后的 RawItem 列表。
    """
    logger.info("=" * 40)
    logger.info("Step 1: Collect")
    logger.info("=" * 40)

    all_items: List[RawItem] = []
    for src in sources:
        if src == "github":
            all_items.extend(_collect_github(limit))
        elif src == "rss":
            all_items.extend(_collect_rss(limit))
        else:
            logger.warning("Unknown source: %s", src)

    logger.info("Total collected: %d items", len(all_items))
    return all_items


# ---------------------------------------------------------------------------
# Step 2: Analyze
# ---------------------------------------------------------------------------


ANALYSIS_SYSTEM_PROMPT = """你是一个 AI 技术分析助手。请分析以下技术内容，以 JSON 格式返回分析结果：

{
  "summary": "一句话中文摘要（20-100字）",
  "description": "详细中文描述（50-100字）",
  "tech_category": "技术分类，如：大语言模型、AI编程工具、多智能体、计算机视觉、金融AI应用",
  "innovation": "创新点说明（一句话）",
  "difficulty": "难度评估：入门/中等/较高/高级",
  "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "use_cases": ["应用场景1", "应用场景2", "应用场景3"],
  "score": 8
}

请只返回 JSON，不要其他文字。"""


def _parse_analysis_json(raw: str) -> Dict[str, Any]:
    """从 LLM 回复中提取并解析 JSON 分析结果。

    Args:
        raw: LLM 回复文本。

    Returns:
        解析后的字典，解析失败时返回部分默认值。
    """
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        logger.warning("No JSON found in LLM response, using defaults")
        return {}

    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON: %s", exc)
        return {}


def analyze(items: List[RawItem], dry_run: bool = False) -> List[Article]:
    """Step 2: 调用 LLM 分析每条内容，生成结构化 Article。

    Args:
        items: 原始数据条目列表。
        dry_run: 为 True 时跳过真实 LLM 调用，使用模拟分析。

    Returns:
        Article 列表。
    """
    logger.info("=" * 40)
    logger.info("Step 2: Analyze")
    logger.info("=" * 40)

    if not items:
        logger.info("No items to analyze")
        return []

    articles: List[Article] = []

    for i, item in enumerate(items):
        logger.info("[%d/%d] Analyzing: %s", i + 1, len(items), item.title)

        if dry_run:
            analysis = _mock_analysis(item)
        else:
            prompt = (
                f"标题：{item.title}\n"
                f"描述：{item.summary}\n"
                f"地址：{item.url}\n"
                f"语言：{item.extra.get('language', 'N/A')}\n"
            )
            try:
                response = chat_with_retry(
                    messages=[
                        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                analysis = _parse_analysis_json(response.content)
            except Exception as exc:
                logger.error("LLM analysis failed for %s: %s", item.title, exc)
                analysis = {}

        article = Article(item, analysis)
        articles.append(article)

        if dry_run:
            logger.info("  -> title=%s tags=%s score=%d",
                        item.title,
                        article.data.get("tags", []),
                        article.data.get("analysis", {}).get("score", 0))

    logger.info("Analyzed %d items", len(articles))
    return articles


def _mock_analysis(item: RawItem) -> Dict[str, Any]:
    """生成模拟分析结果（用于 dry-run 或无 API key 的场景）。

    Args:
        item: 原始数据条目。

    Returns:
        模拟分析字典。
    """
    return {
        "summary": item.summary[:100] if item.summary else item.title[:100],
        "description": item.summary[:80] if item.summary else item.title[:80],
        "tech_category": "AI",
        "innovation": "创新点待分析",
        "difficulty": "中等",
        "tags": [item.source, "ai"],
        "use_cases": ["待分析"],
        "score": 5,
    }


# ---------------------------------------------------------------------------
# Step 3: Organize
# ---------------------------------------------------------------------------


def organize(articles: List[Article]) -> List[Article]:
    """Step 3: 去重、标准化、校验。

    去重规则：相同 source_url 只保留 score 最高的条目。

    Args:
        articles: 待整理的 Article 列表。

    Returns:
        整理后的 Article 列表。
    """
    logger.info("=" * 40)
    logger.info("Step 3: Organize")
    logger.info("=" * 40)

    if not articles:
        return []

    seen: Dict[str, Article] = {}
    for article in articles:
        url = article.source_url
        if not url:
            continue
        if url in seen:
            existing_score = seen[url].data.get("analysis", {}).get("score", 0)
            new_score = article.data.get("analysis", {}).get("score", 0)
            if new_score > existing_score:
                seen[url] = article
                logger.debug("Dedup: keeping %s (score %d > %d)",
                             article.data["title"], new_score, existing_score)
        else:
            seen[url] = article

    deduped = list(seen.values())
    removed = len(articles) - len(deduped)
    if removed:
        logger.info("Removed %d duplicates", removed)

    valid: List[Article] = []
    for article in deduped:
        missing = article.validate()
        if missing:
            logger.warning("Article %s missing fields: %s",
                           article.data.get("id", "?"), missing)
            for field in missing:
                parts = field.split(".")
                if len(parts) == 2 and parts[0] == "analysis":
                    article.data.setdefault("analysis", {})[parts[1]] = ""
                else:
                    article.data[field] = article.data.get(field, "")
        valid.append(article)

    logger.info("Valid articles: %d", len(valid))
    return valid


# ---------------------------------------------------------------------------
# Step 4: Save
# ---------------------------------------------------------------------------


def save(articles: List[Article], dry_run: bool = False) -> None:
    """Step 4: 将文章保存为独立 JSON 文件到 knowledge/articles/。

    Args:
        articles: Article 列表。
        dry_run: 为 True 时只打印不写入文件。
    """
    logger.info("=" * 40)
    logger.info("Step 4: Save")
    logger.info("=" * 40)

    if not articles:
        logger.info("No articles to save")
        return

    output_dir = ARTICLES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for article in articles:
        filepath = output_dir / article.filename
        json_str = article.to_json()

        if dry_run:
            logger.info("[DRY-RUN] Would save: %s (%s)",
                        filepath.name, article.source_url)
            logger.debug("Content:\n%s", json_str)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info("Saved: %s", filepath.name)
            saved_paths.append(str(filepath))

    if saved_paths:
        import importlib
        validate_json = importlib.import_module("hooks.validate_json")
        result = validate_json.ValidationResult()
        for path in saved_paths:
            validate_json.validate_file(path, result)
        if result.passed:
            logger.info("Hook validate_json: all %d files passed validation", len(saved_paths))
        else:
            logger.warning("Hook validate_json: %d/%d files failed validation",
                           result.files_failed, len(saved_paths))
            for error in result.errors:
                logger.warning("  %s", error)


def save_raw(items: List[RawItem], dry_run: bool = False) -> None:
    """将采集的原始数据保存到 knowledge/raw/。

    Args:
        items: RawItem 列表。
        dry_run: 为 True 时只打印不写入。
    """
    if not items:
        return

    sources = set(i.source for i in items)
    for src in sources:
        src_items = [i.to_dict() for i in items if i.source == src]
        filename = f"{src}-{DATE_STAMP}.json"
        filepath = RAW_DIR / filename
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        json_str = json.dumps(src_items, ensure_ascii=False, indent=2)

        if dry_run:
            logger.info("[DRY-RUN] Would save raw: %s (%d items)",
                        filepath.name, len(src_items))
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info("Saved raw: %s (%d items)", filepath.name, len(src_items))


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


INTERMEDIATE_DIR = RAW_DIR / "_intermediate"


def _intermediate_path(date: Optional[str] = None) -> Path:
    """返回分析中间结果文件路径。

    Args:
        date: 日期字符串，为 None 时使用当前日期。

    Returns:
        中间结果文件路径。
    """
    d = date or DATE_STAMP
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    return INTERMEDIATE_DIR / f"analyzed_{d}.json"


def _save_intermediate(articles: List[Article], dry_run: bool = False) -> None:
    """保存分析后的中间结果到磁盘。

    Args:
        articles: Article 列表。
        dry_run: 为 True 时不写入。
    """
    if dry_run or not articles:
        return
    data = [a.data for a in articles]
    path = _intermediate_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved intermediate: %s (%d articles)", path.name, len(articles))


def _load_latest_intermediate() -> List[Dict[str, Any]]:
    """加载最近一次分析步骤保存的中间结果。

    按文件名中的日期后缀降序排序，取最新文件。

    Returns:
        Article 原始数据字典列表，无可用文件时返回空列表。
    """
    if not INTERMEDIATE_DIR.exists():
        return []
    files = sorted(INTERMEDIATE_DIR.glob("analyzed_*.json"), reverse=True)
    if not files:
        return []
    latest = files[0]
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Loaded intermediate: %s (%d articles)", latest.name, len(data))
    return data


def _load_latest_raw() -> List[RawItem]:
    """从 knowledge/raw/ 加载最近一次采集的原始数据。

    Returns:
        RawItem 列表。
    """
    if not RAW_DIR.exists():
        return []
    files = sorted(RAW_DIR.glob("*.json"), reverse=True)
    raw_items: List[RawItem] = []
    for f in files[:3]:
        if f.parent.name == "_intermediate":
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data if isinstance(data, list) else [data]:
            raw_items.append(RawItem(
                title=entry.get("title", ""),
                url=entry.get("url", entry.get("source_url", "")),
                source=entry.get("source", entry.get("source_platform", "unknown")),
                summary=entry.get("summary", ""),
                popularity=entry.get("popularity", 0),
                extra=entry.get("extra", {}),
            ))
    return raw_items


def _rebuild_articles_from_data(data_list: List[Dict[str, Any]]) -> List[Article]:
    """从字典列表重建 Article 对象。

    Args:
        data_list: Article.data 字典列表。

    Returns:
        Article 列表。
    """
    articles: List[Article] = []
    for d in data_list:
        raw = RawItem(
            title=d.get("title", ""),
            url=d.get("source_url", ""),
            source=d.get("source_platform", "unknown"),
            summary=d.get("summary", ""),
        )
        analysis = d.get("analysis", {})
        article = Article(raw, {
            "summary": d.get("summary", ""),
            "tags": d.get("tags", []),
            "description": analysis.get("description", ""),
            "tech_category": analysis.get("tech_category", ""),
            "innovation": analysis.get("innovation", ""),
            "difficulty": analysis.get("difficulty", ""),
            "use_cases": analysis.get("use_cases", []),
            "score": analysis.get("score", 0),
        })
        article.data["id"] = d.get("id", article.data["id"])
        article.data["created_at"] = d.get("created_at", article.data["created_at"])
        article.data["updated_at"] = d.get("updated_at", article.data["updated_at"])
        articles.append(article)
    return articles


def run_pipeline(
    sources: Optional[List[str]] = None,
    limit: int = 10,
    dry_run: bool = False,
    steps: Optional[List[int]] = None,
) -> None:
    """执行流水线：采集 → 分析 → 整理 → 保存，支持指定步骤。

    Args:
        sources: 源名称列表，如 ["github", "rss"]。
        limit: 每个源的最大采集数量。
        dry_run: 为 True 时跳过文件写入。
        steps: 要运行的步骤编号列表（1-4），为 None 时运行全部。
    """
    steps = steps or [1, 2, 3, 4]
    sources = sources or ["github", "rss"]

    logger.info("Pipeline started: sources=%s limit=%d dry_run=%s steps=%s",
                sources, limit, dry_run, steps)

    # Step 1: Collect
    step_collect: List[RawItem] = []
    if 1 in steps:
        step_collect = collect(sources, limit)
        save_raw(step_collect, dry_run=dry_run)
    else:
        step_collect = _load_latest_raw()

    # Step 2: Analyze
    step_analyze: List[Article] = []
    if 2 in steps:
        step_analyze = analyze(step_collect, dry_run=dry_run)
        _save_intermediate(step_analyze, dry_run=dry_run)
    else:
        intermediate_data = _load_latest_intermediate()
        step_analyze = _rebuild_articles_from_data(intermediate_data)

    # Step 3: Organize
    step_organize: List[Article] = []
    if 3 in steps:
        step_organize = organize(step_analyze)

    # Step 4: Save
    if 4 in steps:
        save(step_organize, dry_run=dry_run)

    logger.info("Pipeline finished: %d collected, %d analyzed, %d articles",
                len(step_collect), len(step_analyze), len(step_organize))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 参数列表，为 None 时使用 sys.argv[1:]。

    Returns:
        解析后的命名空间。
    """
    parser = argparse.ArgumentParser(
        description="AI 知识库自动化流水线 — 采集、分析、整理、保存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python pipeline/pipeline.py --sources github,rss --limit 20\n"
            "  python pipeline/pipeline.py --sources github --limit 5\n"
            "  python pipeline/pipeline.py --sources rss --limit 10\n"
            "  python pipeline/pipeline.py --sources github --limit 5 --dry-run\n"
            "  python pipeline/pipeline.py --step 1 --step 2\n"
            "  python pipeline/pipeline.py --step 3 --step 4\n"
            "  python pipeline/pipeline.py --verbose\n"
        ),
    )
    parser.add_argument(
        "--sources",
        default="github,rss",
        help="数据源，逗号分隔（github, rss），默认 github,rss",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="每个源的最大采集数量，默认 10",
    )
    parser.add_argument(
        "--step",
        type=int,
        action="append",
        dest="steps",
        choices=[1, 2, 3, 4],
        help="要运行的步骤编号（可重复，如 --step 1 --step 2），不指定则运行全部",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式：只打印不写入文件",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细日志输出",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    """CLI 入口函数。

    Args:
        argv: 参数列表。
    """
    args = parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    run_pipeline(
        sources=sources,
        limit=args.limit,
        dry_run=args.dry_run,
        steps=args.steps,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _run_tests() -> None:
    """运行单元测试（不依赖网络和环境变量）。"""
    print("=" * 60)
    print("pipeline/pipeline.py 自测")
    print("=" * 60)

    # 1. _slugify
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("  AI / ML @ 2024  ") == "ai-ml-2024"
    assert _slugify("a" * 100) == "a" * 64
    assert _slugify("") == "untitled"
    print("[PASS] _slugify")

    # 2. RawItem
    item = RawItem("Test", "https://example.com", "github", "desc", 100)
    d = item.to_dict()
    assert d["title"] == "Test"
    assert d["popularity"] == 100
    print("[PASS] RawItem")

    # 3. Article construction
    raw = RawItem("Test Repo", "https://github.com/test/repo", "github", "A test repo", 50)
    analysis_data = {
        "summary": "测试仓库",
        "description": "这是一个测试仓库",
        "tech_category": "大语言模型",
        "innovation": "创新点",
        "difficulty": "中等",
        "tags": ["test", "ai"],
        "use_cases": ["测试"],
        "score": 7,
    }
    article = Article(raw, analysis_data)
    assert article.data["source_url"] == "https://github.com/test/repo"
    assert article.data["source_platform"] == "github"
    assert article.data["id"].startswith("test-repo-")
    print("[PASS] Article construction")

    # 4. Article validation (all fields present)
    missing = article.validate()
    assert missing == [], f"Missing fields: {missing}"
    print("[PASS] Article validation (complete)")

    # 5. Article validation (constructor always fills defaults)
    empty_article = Article(raw, {})
    missing = empty_article.validate()
    assert missing == [], f"Constructor should fill defaults: {missing}"
    print("[PASS] Article validation (default fields filled)")

    # 6. _parse_rss_xml
    rss_xml = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>AI News</title>
          <link>https://example.com/ai-news</link>
          <description>Latest AI developments</description>
        </item>
        <item>
          <title>ML Update</title>
          <link>https://example.com/ml-update</link>
          <description>Machine learning update</description>
        </item>
      </channel>
    </rss>"""
    entries = _parse_rss_xml(rss_xml, "test")
    assert len(entries) == 2
    assert entries[0]["title"] == "AI News"
    assert entries[1]["link"] == "https://example.com/ml-update"
    print("[PASS] _parse_rss_xml")

    # 7. _parse_rss_xml Atom format
    atom_xml = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Atom Entry</title>
        <link>https://example.com/atom</link>
        <description>Atom description</description>
      </entry>
    </feed>"""
    entries = _parse_rss_xml(atom_xml, "test-atom")
    assert len(entries) == 1
    assert entries[0]["title"] == "Atom Entry"
    print("[PASS] _parse_rss_xml (Atom)")

    # 8. _parse_analysis_json
    result = _parse_analysis_json('{"summary": "test", "score": 8}')
    assert result["summary"] == "test"
    assert result["score"] == 8
    print("[PASS] _parse_analysis_json (valid)")

    # 9. _parse_analysis_json with markdown wrapping
    result = _parse_analysis_json('```json\n{"summary": "wrapped", "tags": ["a"]}\n```')
    assert result["summary"] == "wrapped"
    print("[PASS] _parse_analysis_json (markdown-wrapped)")

    # 10. _parse_analysis_json invalid
    result = _parse_analysis_json("Not JSON at all")
    assert result == {}
    print("[PASS] _parse_analysis_json (invalid)")

    # 11. _mock_analysis
    mock = _mock_analysis(RawItem("Repo", "https://x.com", "github", "desc", 10))
    assert mock["score"] == 5
    assert "ai" in mock["tags"]
    print("[PASS] _mock_analysis")

    # 12. Article filename
    raw2 = RawItem("My Great Project!", "https://x.com", "github", "", 0)
    article2 = Article(raw2, {})
    assert article2.filename == f"{DATE_STAMP}-my-great-project.json"
    print("[PASS] Article filename")

    # 13. organize dedup
    raw_a = RawItem("A", "https://x.com/a", "github", "desc a", 10)
    raw_b = RawItem("A (dup)", "https://x.com/a", "github", "desc b", 20)
    articles_in = [
        Article(raw_a, {"score": 5, "summary": "a", "tags": []}),
        Article(raw_b, {"score": 8, "summary": "b", "tags": []}),
    ]
    organized = organize(articles_in)
    assert len(organized) == 1
    assert organized[0].data["title"] == "A (dup)"
    print("[PASS] organize dedup")

    # 14. collect with empty sources
    result = collect([], 10)
    assert result == []
    print("[PASS] collect empty sources")

    print()
    print("=" * 60)
    print("全部测试通过")
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_tests()
    else:
        main()
