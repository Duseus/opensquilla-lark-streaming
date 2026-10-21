"""卡片 JSON 构建（CardKit 2.0）。

结构对齐 Hermes 的飞书卡片：

    ┌───────────────────────────────┐
    │  💭 Tanuki 处理中…      (blue) │  header
    │  回答正文（流式刷新的 markdown）│  element_id=content
    │  ▶ 🧠 9 轮 · 🛠️ 53 个工具 · ⏳ 10 分 9 秒
    │      第 1 轮 · 0.0s           │  collapsible_panel
    │      Run command (201 ms)     │  element_id=agent_process_panel
    │      git diff ...             │
    │  ─────────────────────────    │  hr
    │  ✅ 已完成 · 4m 11s · ⚕model  │  footer markdown
    │  ☀️ 天气                       │
    │  💬 一言                       │
    └───────────────────────────────┘
"""

from __future__ import annotations

import time
from typing import Any

from .descriptors import describe_tool, resolve_descriptor, tool_detail
from .metrics import compact_num, footer_elapsed, human_duration, resolve_context_window

MAX_BODY_CHARS = 18_000
# 飞书单卡元素上限约 200，留出余量后再裁剪历史步骤
MAX_PANEL_ELEMENTS = 150
KEEP_PANEL_ELEMENTS = 140


def panel_title(tool_count: int, round_count: int, elapsed_s: float) -> str:
    """面板折叠态标题：``🧠 9 轮 · 🛠️ 53 个工具 · ⏳ 10 分 9 秒``。"""
    return (
        f"🧠 {int(round_count)} 轮 · 🛠️ {int(tool_count)} 个工具"
        f" · ⏳ {human_duration(elapsed_s)}"
    )


def _round_row(item: dict[str, Any], now: float) -> dict[str, Any]:
    started = item.get("started")
    started = now if started is None else float(started)
    ended = item.get("ended")
    ended = now if ended is None else float(ended)
    duration = max(ended - started, 0.0)
    color = "green" if item.get("ended") else "orange"
    return {
        "tag": "div",
        "icon": {
            "tag": "standard_icon",
            "token": "robot-add_outlined",
            "size": "16px 16px",
            "color": "grey",
        },
        "text": {
            "tag": "lark_md",
            "content": f"<font color='{color}'>**第 {item.get('n')} 轮 · {duration:.1f}s**</font>",
            "text_size": "notation",
        },
    }


def _preview_row(text: str) -> dict[str, Any] | None:
    preview = "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())
    if not preview:
        return None
    limit = 1200
    return {
        "tag": "div",
        "margin": "0px 0px 0px 22px",
        "text": {
            "tag": "lark_md",
            "content": preview[:limit] + ("…" if len(preview) > limit else ""),
            "text_size": "notation",
        },
    }


def _tool_row(tool: dict[str, Any]) -> dict[str, Any]:
    ok = tool.get("ok")
    if ok is None:
        color = "turquoise"
    elif ok:
        color = "green"
    else:
        color = "red"
    elapsed_ms = None
    if tool.get("elapsed") is not None:
        elapsed_ms = float(tool["elapsed"]) * 1000
    title, icon = describe_tool(tool.get("name"), elapsed_ms)
    return {
        "tag": "div",
        "icon": {"tag": "standard_icon", "token": icon, "color": "grey"},
        "text": {
            "tag": "lark_md",
            "content": f"<font color='{color}'>**{title}**</font>",
            "text_size": "notation",
        },
    }


def _detail_row(tool: dict[str, Any]) -> dict[str, Any] | None:
    detail = (tool.get("detail") or "").strip()
    if not detail:
        return None
    return {
        "tag": "div",
        "margin": "0px 0px 0px 22px",
        "text": {
            "tag": "plain_text",
            "content": detail,
            "text_color": "grey",
            "text_size": "notation",
        },
    }


def round_elements(rounds: list[dict[str, Any]], now: float | None = None) -> list[dict[str, Any]]:
    """把轮次/工具状态渲染成面板子元素。

    超过 ``MAX_PANEL_ELEMENTS`` 时保留最近 ``KEEP_PANEL_ELEMENTS`` 项并前置提示，
    正常长度下全量渲染，点开折叠面板就能看到每一步。
    """
    now = time.monotonic() if now is None else now
    rows: list[dict[str, Any]] = []
    for item in rounds:
        rows.append(_round_row(item, now))
        preview = _preview_row(item.get("text") or "")
        if preview:
            rows.append(preview)
        for tool in item.get("tools") or []:
            rows.append(_tool_row(tool))
            detail = _detail_row(tool)
            if detail:
                rows.append(detail)

    if len(rows) > MAX_PANEL_ELEMENTS:
        hidden = len(rows) - KEEP_PANEL_ELEMENTS
        rows = [
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"⚡ 还有 {hidden} 项已折叠（超出卡片上限）",
                    "text_color": "grey",
                    "text_size": "notation",
                },
            }
        ] + rows[-KEEP_PANEL_ELEMENTS:]
    return rows


def footer_text(
    *,
    done: bool,
    failed: bool,
    model: str,
    weather: str,
    hitokoto: str,
    elapsed_s: float = 0.0,
    usage: dict[str, Any] | None = None,
) -> str:
    """底栏三行：状态指标 / 天气 / 一言。

    指标行示例::

        ✅ 已完成 · 4m 11s · ⚕gemini-3.8-flash-high · 输入 10.0M 输出 18.0K 思考 4.4K · 159.9K/1.0M (15%)
    """
    if failed:
        status = "⚠️ 已中止"
    elif done:
        status = "✅ 已完成"
    else:
        status = "💭 处理中"

    parts = [status]
    if elapsed_s:
        parts.append(footer_elapsed(elapsed_s))
    if model:
        parts.append(f"⚕{model.split('/')[-1]}")

    usage = usage or {}
    input_tokens = int(usage.get("input") or 0)
    output_tokens = int(usage.get("output") or 0)
    reasoning_tokens = int(usage.get("reasoning") or 0)
    if input_tokens or output_tokens:
        metrics = [f"输入 {compact_num(input_tokens)}", f"输出 {compact_num(output_tokens)}"]
        if reasoning_tokens:
            metrics.append(f"思考 {compact_num(reasoning_tokens)}")
        parts.append(" ".join(metrics))

    window = resolve_context_window(model)
    if window and input_tokens:
        # DoneEvent 只给本轮累计输入，按迭代次数折算近似上下文占用
        iterations = max(int(usage.get("iterations") or 1), 1)
        used_context = min(input_tokens // iterations, window)
        parts.append(
            f"{compact_num(used_context)}/{compact_num(window)}"
            f" ({used_context * 100 // window}%)"
        )

    lines = [" · ".join(parts)]
    if weather:
        lines.append(weather)
    if hitokoto:
        lines.append(f"💬 {hitokoto}")
    return "\n\n".join(lines)


def build_card(
    *,
    text: str,
    done: bool = False,
    failed: bool = False,
    rounds: list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
    model: str = "",
    elapsed_s: float = 0.0,
    weather: str = "",
    hitokoto: str = "",
    usage: dict[str, Any] | None = None,
    agent_name: str = "Tanuki",
) -> dict[str, Any]:
    """构建整张卡片 JSON。"""
    rounds = rounds or []
    tools = tools or []

    if failed:
        template = "red"
        title = "⚠️ 已中止"
    elif done:
        template = "green"
        title = "✅ 已完成"
    else:
        template = "blue"
        title = f"💭 {agent_name} 处理中..."

    body = text if text.strip() else " "
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n\n...（内容过长，已截断）"

    elements: list[dict[str, Any]] = [
        {
            "tag": "markdown",
            "element_id": "content",
            "content": body,
            "text_align": "left",
            "margin": "0px 0px 0px 0px",
        }
    ]

    if rounds or tools:
        elements.append(
            {
                "tag": "collapsible_panel",
                "element_id": "agent_process_panel",
                "expanded": False,
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": panel_title(len(tools), len(rounds), elapsed_s),
                        "text_color": "grey",
                        "text_size": "notation",
                    },
                    "vertical_align": "center",
                    "icon": {
                        "tag": "standard_icon",
                        "token": "down-small-ccm_outlined",
                        "size": "16px 16px",
                        "color": "grey",
                    },
                    "icon_position": "right",
                    "icon_expanded_angle": -180,
                },
                "border": {"color": "grey", "corner_radius": "5px"},
                "vertical_spacing": "4px",
                "padding": "8px 8px 8px 8px",
                "elements": round_elements(rounds),
            }
        )

    elements.append({"tag": "hr"})
    elements.append(
        {
            "tag": "markdown",
            "element_id": "footer_status",
            "content": footer_text(
                done=done,
                failed=failed,
                model=model,
                weather=weather,
                hitokoto=hitokoto,
                elapsed_s=elapsed_s,
                usage=usage,
            ),
            "text_size": "notation",
        }
    )

    summary = (text or "").strip()[:60] or agent_name
    return {
        "schema": "2.0",
        "config": {
            "streaming_mode": not done,
            "update_multi": True,
            "summary": {"content": summary},
        },
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        },
        "body": {"elements": elements},
    }


__all__ = [
    "build_card",
    "footer_text",
    "panel_title",
    "round_elements",
    "resolve_descriptor",
    "tool_detail",
]
