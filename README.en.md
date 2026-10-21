# OpenSquilla Lark Streaming

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Streaming Feishu (Lark) cards for [OpenSquilla](https://pypi.org/project/opensquilla/) — the reply streams in one message, tool calls and reasoning become an expandable panel, and the card turns green when the turn completes.

Built on the native CardKit 2.0 API. No extra runtime dependencies.

[中文](README.md)

---

## What it looks like

```
┌──────────────────────────────────────────────────┐
│  💭 Tanuki processing…                   (blue)  │
│  The root cause is a stale DNS cache. Let me run │
│  the keepalive script and check the logs.        │
│  ▶ 🧠 5 rounds · 🛠️ 8 tools · ⏳ 9.7s            │
│      第 1 轮 · 0.7s                              │
│      Run command (352 ms)                        │
│      bash instabox_fleet_keepalive.sh            │
│  ────────────────────────────────────────────    │
│  ✅ 已完成 · 4m 11s · ⚕gemini-3.8-flash-high     │
│  输入 10.0M 输出 18.0K 思考 4.4K · 159.9K/1.0M (15%) │
│  ☀️ 临平 20.6°C/14.3°C                           │
│  💬 「保持好奇，持续折腾。」                     │
└──────────────────────────────────────────────────┘
```

Blue while streaming, green when done, red on failure. The panel is fully expandable — nothing is silently trimmed below 150 elements.

## Features

- CardKit 2.0 streaming body with element-level incremental updates
- Reasoning rounds grouped automatically, each with elapsed time
- Tool steps rendered as `Run command (201 ms)` + the real command / file / query
- Token metrics (input, output, reasoning) and context usage
- Weather and a daily quote in the footer, with graceful fallback
- Falls back to a plain text message if card creation fails

## Install

```bash
pip install opensquilla-lark-streaming
osls install
systemctl --user restart opensquilla-gateway
```

`osls install` appends a 6-line shim to `opensquilla/channels/feishu.py`; the actual card logic lives in this package and is attached at runtime via `patch.apply(FeishuChannel)`.

Uninstall:

```bash
osls uninstall && systemctl --user restart opensquilla-gateway
```

## How it works

OpenSquilla emits `thinking`, `tool_use_start`, `tool_result`, `router_decision`, `done` events. This package forwards them to `note_stream_event()`, folds them into rounds/tools/usage, and re-renders the card through CardKit.

The only patch to OpenSquilla's own dispatch is forwarding the `done` event — without it the channel never sees token usage.

## Known trade-offs

- Context usage is estimated as `input_tokens / iterations`; `DoneEvent` does not expose the live context length.
- Upgrading OpenSquilla overwrites the shim — re-run `osls install`.

## License

MIT © Duseus
