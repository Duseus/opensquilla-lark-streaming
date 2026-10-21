"""工具描述符：把模型侧的工具名翻译成人类可读的标题、图标和明细行。

设计目标与 Hermes / fry-cards 卡片一致：
    Run command (201 ms)
    bash instabox_fleet_keepalive.sh
即「动词短语 + 耗时」作标题，真实参数作缩进明细。
"""

from __future__ import annotations

import json
from typing import Any

# aliases: 命中的工具名前缀（大小写、-/_ 均已归一化）
TOOL_DESCRIPTORS: list[dict[str, Any]] = [
    {"aliases": ["skill"], "icon": "app-default_outlined", "title": "Load skill"},
    {
        "aliases": ["read", "open"],
        "icon": "file-link-text_outlined",
        "title": "Read",
        "sanitizer": "path",
    },
    {
        "aliases": ["write", "edit"],
        "icon": "edit_outlined",
        "title": "Edit",
        "sanitizer": "path",
    },
    {
        "aliases": ["web_search", "web-search", "search"],
        "icon": "search_outlined",
        "title": "Search",
        "sanitizer": "search",
    },
    {
        "aliases": ["web_fetch", "web-fetch", "fetch"],
        "icon": "language_outlined",
        "title": "Fetch web page",
        "sanitizer": "url",
    },
    {"aliases": ["grep"], "icon": "doc-search_outlined", "title": "Search text", "sanitizer": "search"},
    {"aliases": ["glob"], "icon": "folder_outlined", "title": "Search files", "sanitizer": "path"},
    {
        "aliases": ["exec", "bash", "command", "run", "shell", "terminal", "ssh"],
        "icon": "setting_outlined",
        "title": "Run command",
        "sanitizer": "command",
    },
    {"aliases": ["browser", "playwright", "navigate"], "icon": "browser-mac_outlined", "title": "Browser"},
    {"aliases": ["agent", "task", "spawn"], "icon": "robot_outlined", "title": "Run sub-agent"},
    {"aliases": ["check", "determine", "verify"], "icon": "list-check_outlined", "title": "Check"},
    {"aliases": ["analyze", "summarize", "prepare"], "icon": "report_outlined", "title": "Analyze"},
    {"aliases": ["clarify"], "icon": "chat_outlined", "title": "Clarify"},
]

DEFAULT_TOOL_ICON = "tool_02"


def _normalize(name: str | None) -> str:
    return (name or "").strip().lower().replace("-", "_")


def resolve_descriptor(name: str | None) -> dict[str, Any] | None:
    """按别名表解析工具描述符，未命中返回 None。"""
    normalized = _normalize(name)
    if not normalized:
        return None
    for desc in TOOL_DESCRIPTORS:
        for alias in desc["aliases"]:
            alias_norm = alias.replace("-", "_")
            if normalized == alias_norm or normalized.startswith(f"{alias_norm}_"):
                return desc
    return None


def humanize_tool_name(name: str | None) -> str:
    """未登记的工具名兜底：下划线转空格并首字母大写。"""
    cleaned = (name or "").replace("-", " ").replace("_", " ").strip()
    if not cleaned:
        return "Tool"
    return cleaned[0].upper() + cleaned[1:]


def describe_tool(name: str | None, elapsed_ms: float | None = None) -> tuple[str, str]:
    """返回 (标题, 图标)。

    标题形如 ``Run command (201 ms)``；elapsed_ms 为空时只返回动词短语。
    """
    desc = resolve_descriptor(name) or {}
    title = desc.get("title") or humanize_tool_name(name)
    icon = desc.get("icon", DEFAULT_TOOL_ICON)
    if elapsed_ms is not None:
        title = f"{title} ({format_duration_ms(elapsed_ms)})"
    return title, icon


def format_duration_ms(ms: float) -> str:
    """毫秒 → ``201 ms`` / ``2.1 s``（Hermes 卡片写法）。"""
    ms = max(float(ms or 0.0), 0.0)
    return f"{ms:.0f} ms" if ms < 1000 else f"{ms / 1000:.1f} s"


def _first_present(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return None


def tool_detail(name: str | None, arguments: Any) -> str:
    """从工具参数里挑一条最有信息量的明细，压成单行。

    - 命令类取 command/cmd/script
    - 文件类取 file_path/path，只留 basename
    - 搜索类取 query/pattern
    - 其余退化为紧凑 JSON
    """
    if not isinstance(arguments, dict):
        return ""
    desc = resolve_descriptor(name) or {}
    sanitizer = desc.get("sanitizer")
    value: Any = None
    if sanitizer == "command":
        value = _first_present(arguments, ("command", "cmd", "script"))
    elif sanitizer == "path":
        value = _first_present(arguments, ("file_path", "path", "pattern"))
    elif sanitizer == "search":
        value = _first_present(arguments, ("query", "pattern", "q"))
    elif sanitizer == "url":
        value = _first_present(arguments, ("url",))
    if value is None:
        value = _first_present(arguments, ("command", "query", "file_path", "path", "url", "pattern"))
    if value is None:
        try:
            value = json.dumps(arguments, ensure_ascii=False)
        except (TypeError, ValueError):
            return ""

    text = str(value)
    if sanitizer == "path" or (text.startswith("/") and " " not in text):
        text = text.replace("\\", "/").rstrip("/").split("/")[-1]
    text = " ".join(text.split())
    return text[:160] + ("…" if len(text) > 160 else "")
