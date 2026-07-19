"""Hook event dispatcher — 扫描 hooks 目录并触发对应事件处理函数。"""

import importlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HOOKS_DIR = Path(__file__).parent

SKIP_MODULES = frozenset({"__init__", "dispatcher"})


def _discover_hook_modules() -> list[str]:
    """发现 hooks 目录下所有可用的 hook 模块名。"""
    modules: list[str] = []
    for f in HOOKS_DIR.glob("*.py"):
        name = f.stem
        if name not in SKIP_MODULES:
            modules.append(name)
    return sorted(modules)


def fire(event_name: str, **context: Any) -> None:
    """触发指定事件，调用所有 hook 中对应的事件处理函数。

    Args:
        event_name: 事件名称，如 "after_save"。
        **context: 传递给 hook 处理函数的上下文参数。
    """
    handler_name = f"handle_{event_name}"
    for module_name in _discover_hook_modules():
        try:
            mod = importlib.import_module(f"hooks.{module_name}")
        except Exception as exc:
            logger.warning("Hook %s 加载失败: %s", module_name, exc)
            continue
        handler = getattr(mod, handler_name, None)
        if handler is None:
            continue
        try:
            handler(**context)
        except Exception as exc:
            logger.error("Hook %s.%s 执行失败: %s", module_name, handler_name, exc)
