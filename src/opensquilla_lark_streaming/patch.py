"""把流式卡片能力注入 OpenSquilla 的 FeishuChannel。

设计原则：**不复制 OpenSquilla 源码**，只在运行时给类打补丁。

    from opensquilla_lark_streaming import patch
    patch.apply(FeishuChannel)

注入的内容：

* ``send_streaming``           —— CardKit 建卡 / 增量刷字 / 封卡
* ``note_stream_event``        —— 思考、工具、模型路由、token 用量进面板与底栏
* ``_cardkit_*`` 系列辅助方法  —— 建卡、更新元素、结束卡片

另外给 ``gateway.channel_dispatch._RuntimeChannelStreamRelay`` 补上 ``done``
事件转发，否则通道拿不到 token 统计。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import time
from typing import Any

from .card import build_card
from .metrics import fetch_hitokoto, fetch_weather

MARKER = "_opensquilla_lark_streaming_applied"

TOOL_EVENT_KINDS = ("tool_use_start", "tool_result", "thinking", "router_decision", "done")


def _module_ns(channel_cls: type) -> dict[str, Any]:
    module = importlib.import_module(channel_cls.__module__)
    required = ("retry_request", "OutgoingMessage", "FeishuApiError", "_feishu_receive_id_type")
    missing = [name for name in required if name not in module.__dict__]
    if missing:
        raise RuntimeError(
            f"OpenSquilla 版本不兼容，缺少: {', '.join(missing)}（模块 {module.__name__}）"
        )
    return module.__dict__


def _patch_dispatch() -> bool:
    """把 Thinking/Tool/Done 事件转发给通道，并让 relay 实时吐字。

    两代 OpenSquilla 的结构不同：

    * 0.3.x：``_RuntimeChannelStreamRelay._forward_tool_event(event)`` 逐事件转发；
    * 0.5.x：只有 ``relay.emit(event)``，通道侧拿不到事件，且正文默认攒到
      Done 才交付（没有打字效果）。
    """
    try:
        dispatch = importlib.import_module("opensquilla.gateway.channel_dispatch")
        relay_cls = getattr(dispatch, "_RuntimeChannelStreamRelay", None)
    except Exception:  # noqa: BLE001 - 不同版本结构可能不同，降级即可
        return False
    if relay_cls is None:
        return False

    # ---- OpenSquilla 0.5+ ----
    if callable(getattr(relay_cls, "emit", None)) and not hasattr(relay_cls, "_forward_tool_event"):
        if getattr(relay_cls, "_osls_emit_patched", False):
            return True

        original_emit = relay_cls.emit

        async def emit(self: Any, event: Any) -> None:
            await original_emit(self, event)
            hook = getattr(getattr(self, "_channel", None), "note_stream_event", None)
            if not callable(hook):
                return
            try:
                await hook(event)
            except Exception:  # noqa: BLE001 - 渲染失败不能影响回复
                pass

        original_init = relay_cls.__init__

        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            # 强制实时预览：否则 relay 只在 Done 时一次性交付，卡片没有打字效果
            self._live_preview = True

        emit._osls_emit_patched = True  # type: ignore[attr-defined]
        relay_cls.emit = emit  # noqa: SLF001
        relay_cls.__init__ = __init__  # noqa: SLF001
        relay_cls._osls_emit_patched = True  # noqa: SLF001
        return True

    # ---- OpenSquilla 0.3.x ----
    original = getattr(relay_cls, "_forward_tool_event", None)
    if original is None:
        return False
    if getattr(original, "_osls_patched", False):
        return True

    async def _forward_tool_event(self: Any, event: Any) -> None:
        hook = getattr(self._channel, "note_stream_event", None)
        if not callable(hook):
            return
        if getattr(event, "kind", None) not in TOOL_EVENT_KINDS:
            return
        try:
            await hook(event)
        except Exception:  # noqa: BLE001 - 渲染失败不能影响回复
            pass

    _forward_tool_event._osls_patched = True  # type: ignore[attr-defined]
    relay_cls._forward_tool_event = _forward_tool_event  # noqa: SLF001
    return True


def apply(channel_cls: type, *, agent_name: str = "Tanuki") -> bool:
    """给 FeishuChannel 打上流式卡片能力，重复调用安全。"""
    if getattr(channel_cls, MARKER, False):
        return True

    ns = _module_ns(channel_cls)
    retry_request = ns["retry_request"]
    OutgoingMessage = ns["OutgoingMessage"]
    FeishuApiError = ns["FeishuApiError"]
    receive_id_type_of = ns["_feishu_receive_id_type"]
    log = ns.get("log")

    # 0.5.x 的 FeishuChannel 声明 STREAM_UPDATE_STRATEGY="final_only"，
    # 会让 relay 直接跳过流式通道（只调用 channel.send 发纯文本）。
    # 旧的源码补丁是直接改这个常量，现在必须运行期覆盖。
    channel_cls.STREAM_UPDATE_STRATEGY = "adapter_stream"
    channel_cls.stream_update_strategy = "adapter_stream"

    async def send_streaming(
        self: Any,
        chunks: Any,
        *,
        chat_id: str | None = None,
        update_interval_ms: int = 350,
        **kwargs: Any,
    ) -> str | None:
        del kwargs  # 新版本可能传额外路由参数，卡片只用 chat_id
        target = chat_id or self.config.default_chat_id
        accumulated = ""
        card_id: str | None = None
        message_id: str | None = None
        last_push = 0.0
        interval_s = max(update_interval_ms, 120) / 1000.0
        state: dict[str, Any] = {
            "card_id": None,
            "seq": 1,
            "tools": [],
            "rounds": [],
            "cur_round": None,
            "reasoning": 0,
            "last_kind": None,
            "model": "",
            "text": "",
            "weather": "",
            "hitokoto": "",
            "usage": {},
            "lock": asyncio.Lock(),
            "started": time.monotonic(),
        }
        self._stream_state = state

        async def push_content(content: str) -> None:
            async with state["lock"]:
                current = state.get("card_id")
                if not current:
                    return
                seq = int(state["seq"])
                state["seq"] = seq + 1
                await _cardkit_update_element(self, current, "content", content, seq)

        try:
            async for chunk in chunks:
                if not chunk:
                    continue
                accumulated += chunk
                state["text"] = accumulated
                now = time.monotonic()
                if card_id is None:
                    if not accumulated.strip():
                        continue
                    card_id, message_id = await _cardkit_create_and_send(self, target, accumulated, state)
                    state["card_id"] = card_id
                    asyncio.create_task(_load_footer(self, state))
                    last_push = now
                    continue
                if now - last_push >= interval_s:
                    await push_content(accumulated)
                    last_push = now

            if not accumulated.strip() and not state["tools"] and not state["rounds"]:
                return None
            if card_id is None:
                card_id, message_id = await _cardkit_create_and_send(self, target, accumulated, state)
                state["card_id"] = card_id
                asyncio.create_task(_load_footer(self, state))
            await push_content(accumulated)
            await _cardkit_finish(self, card_id, accumulated, state, failed=False)
            return message_id
        except Exception as exc:  # noqa: BLE001 - 流式失败要退回普通消息
            if log is not None:
                log.warning(
                    "feishu.streaming_card_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            if card_id is not None:
                try:
                    await _cardkit_finish(self, card_id, accumulated, state, failed=True)
                except Exception:  # noqa: BLE001
                    pass
                return message_id
            await self.send(OutgoingMessage(content=accumulated, reply_to=target))
            return None

    async def _load_footer(self: Any, state: dict[str, Any]) -> None:
        """后台取天气/一言，取到后刷新一次卡片。"""
        try:
            weather, hitokoto = await asyncio.gather(
                asyncio.to_thread(fetch_weather),
                asyncio.to_thread(fetch_hitokoto),
            )
        except Exception:  # noqa: BLE001
            return
        state["weather"] = weather or ""
        state["hitokoto"] = hitokoto or ""
        if not state.get("card_id"):
            return
        try:
            await _refresh_card(self, state, done=False)
        except Exception:  # noqa: BLE001
            pass

    def _new_round(state: dict[str, Any]) -> dict[str, Any]:
        rounds = state.setdefault("rounds", [])
        item = {
            "n": len(rounds) + 1,
            "started": time.monotonic(),
            "ended": None,
            "text": "",
            "tools": [],
        }
        rounds.append(item)
        state["cur_round"] = item
        state["reasoning"] = len(rounds)
        return item

    async def note_stream_event(self: Any, event: Any) -> None:
        """把思考/工具/路由/done 事件折叠进卡片。"""
        state = getattr(self, "_stream_state", None)
        if not state:
            return
        kind = getattr(event, "kind", None)
        changed = False

        if kind == "thinking":
            current = state.get("cur_round")
            if current is None or state.get("last_kind") == "tool":
                if current is not None and current.get("ended") is None:
                    current["ended"] = time.monotonic()
                current = _new_round(state)
                changed = True
            text = getattr(event, "text", "") or ""
            if text and len(current["text"]) < 4000:
                current["text"] += text
            state["last_kind"] = "thinking"

        elif kind == "tool_use_start":
            current = state.get("cur_round") or _new_round(state)
            tool = {
                "id": getattr(event, "tool_use_id", ""),
                "name": getattr(event, "tool_name", "") or "tool",
                "ok": None,
                "started": time.monotonic(),
                "elapsed": None,
                "detail": "",
            }
            state["tools"].append(tool)
            current["tools"].append(tool)
            state["last_kind"] = "tool"
            changed = True

        elif kind == "tool_result":
            tool_id = getattr(event, "tool_use_id", "")
            name = getattr(event, "tool_name", "") or "tool"
            ok = not bool(getattr(event, "is_error", False))
            tool = next((item for item in state["tools"] if tool_id and item.get("id") == tool_id), None)
            if tool is None:
                current = state.get("cur_round") or _new_round(state)
                tool = {
                    "id": tool_id,
                    "name": name,
                    "ok": None,
                    "started": time.monotonic(),
                    "elapsed": None,
                    "detail": "",
                }
                state["tools"].append(tool)
                current["tools"].append(tool)
            tool["ok"] = ok
            tool["name"] = tool.get("name") or name
            if tool.get("started"):
                tool["elapsed"] = max(time.monotonic() - tool["started"], 0.0)
            from .descriptors import tool_detail

            tool["detail"] = tool_detail(name, getattr(event, "arguments", None))
            state["last_kind"] = "tool"
            changed = True

        elif kind == "router_decision":
            model = getattr(event, "model", "") or ""
            if model and model != state.get("model"):
                state["model"] = model
                changed = True
            state["last_kind"] = "router"

        elif kind == "done":
            state["usage"] = {
                "input": int(getattr(event, "input_tokens", 0) or 0),
                "output": int(getattr(event, "output_tokens", 0) or 0),
                "reasoning": int(getattr(event, "reasoning_tokens", 0) or 0),
                "cached": int(getattr(event, "cached_tokens", 0) or 0),
                "iterations": int(getattr(event, "iterations", 0) or 0),
            }
            if getattr(event, "model", ""):
                state["model"] = event.model
            state["last_kind"] = "done"
            if state.get("card_id"):
                await _refresh_card(self, state, done=False)
            return

        else:
            return

        if not changed or not state.get("card_id"):
            return
        await _refresh_card(self, state, done=False)

    async def _refresh_card(
        self: Any, state: dict[str, Any], *, done: bool, failed: bool = False
    ) -> None:
        async with state["lock"]:
            card_id = state.get("card_id")
            if not card_id:
                return
            seq = int(state["seq"])
            state["seq"] = seq + 1
            now = time.monotonic()
            elapsed = max(now - float(state.get("started", now)), 0.0)
            rounds = state.get("rounds") or []
            if done and rounds and rounds[-1].get("ended") is None:
                rounds[-1]["ended"] = now
            card = build_card(
                text=state.get("text") or "",
                done=done,
                failed=failed,
                rounds=rounds,
                tools=state.get("tools") or [],
                model=str(state.get("model") or ""),
                elapsed_s=elapsed,
                weather=str(state.get("weather") or ""),
                hitokoto=str(state.get("hitokoto") or ""),
                usage=state.get("usage") or {},
                agent_name=agent_name,
            )
            await _cardkit_request(
                self,
                "put",
                f"/cardkit/v1/cards/{card_id}",
                {"card": {"type": "card_json", "data": json.dumps(card, ensure_ascii=False)}, "sequence": seq},
            )

    async def _cardkit_request(
        self: Any, method: str, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        await self._rate_limiter.acquire()
        headers = await self._auth_headers()
        response = await retry_request(
            getattr(self._get_client(), method), path, json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        self._raise_api_error(data, "cardkit request failed")
        out = data.get("data", {})
        return out if isinstance(out, dict) else {}

    async def _cardkit_create_and_send(
        self: Any, chat_id: str, text: str, state: dict[str, Any] | None = None
    ) -> tuple[str, str]:
        state = state or {}
        card = build_card(
            text=text,
            rounds=state.get("rounds") or [],
            tools=state.get("tools") or [],
            model=str(state.get("model") or ""),
            weather=str(state.get("weather") or ""),
            hitokoto=str(state.get("hitokoto") or ""),
            usage=state.get("usage") or {},
            agent_name=agent_name,
        )
        created = await _cardkit_request(
            self, "post", "/cardkit/v1/cards", {"type": "card_json", "data": json.dumps(card, ensure_ascii=False)}
        )
        card_id = str(created.get("card_id") or "")
        if not card_id:
            raise FeishuApiError("cardkit create returned no card_id")
        receive_id_type = receive_id_type_of(chat_id)
        sent = await _cardkit_request(
            self,
            "post",
            f"/im/v1/messages?receive_id_type={receive_id_type}",
            {
                "receive_id": chat_id,
                "msg_type": "interactive",
                "content": json.dumps({"type": "card", "data": {"card_id": card_id}}),
            },
        )
        return card_id, str(sent.get("message_id") or "")

    async def _cardkit_update_element(
        self: Any, card_id: str, element_id: str, content: str, sequence: int
    ) -> None:
        body = content if content and content.strip() else " "
        if len(body) > 18_000:
            body = body[:18_000] + "\n\n...（内容过长，已截断）"
        await _cardkit_request(
            self,
            "put",
            f"/cardkit/v1/cards/{card_id}/elements/{element_id}/content",
            {"content": body, "sequence": sequence},
        )

    async def _cardkit_finish(
        self: Any, card_id: str, text: str, state: dict[str, Any], *, failed: bool = False
    ) -> None:
        state["card_id"] = card_id
        state["text"] = text
        await _refresh_card(self, state, done=True, failed=failed)

    for name, func in (
        ("send_streaming", send_streaming),
        ("note_stream_event", note_stream_event),
        ("_load_footer", _load_footer),
        ("_refresh_card", _refresh_card),
        ("_cardkit_request", _cardkit_request),
        ("_cardkit_create_and_send", _cardkit_create_and_send),
        ("_cardkit_update_element", _cardkit_update_element),
        ("_cardkit_finish", _cardkit_finish),
    ):
        setattr(channel_cls, name, func)

    setattr(channel_cls, MARKER, True)
    _patch_dispatch()
    return True


__all__ = ["apply"]
