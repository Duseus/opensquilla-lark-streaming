"""OpenSquilla 飞书流式卡片。

纯函数模块：只负责把事件状态渲染成飞书 CardKit 2.0 卡片 JSON，
不依赖 OpenSquilla 运行时，方便单测与复用。
"""

from .card import build_card, footer_text, panel_title
from .descriptors import describe_tool, format_duration_ms, tool_detail
from .metrics import compact_num, fetch_hitokoto, fetch_weather, footer_elapsed, human_duration

__all__ = [
    "build_card",
    "footer_text",
    "panel_title",
    "describe_tool",
    "format_duration_ms",
    "tool_detail",
    "compact_num",
    "footer_elapsed",
    "human_duration",
    "fetch_weather",
    "fetch_hitokoto",
]

__version__ = "0.1.7"
