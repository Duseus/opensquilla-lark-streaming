# v0.1.2 — 适配 OpenSquilla 0.5.6

Box 从 0.3.0 升到 0.5.6 后，旧补丁失效（`_RuntimeChannelStreamRelay` 没有 `_forward_tool_event` 了）。这版修好并保持向下兼容。

## 变化

| 项 | 0.3.x 路径 | 0.5.x 路径（新增） |
|---|---|---|
| 事件转发 | `relay._forward_tool_event` | 覆写 `relay.emit(event)` |
| 实时打字 | relay 默认实时 | 强制 `_live_preview = True`（0.5.x 默认攒到 Done 才交付）|
| `send_streaming` | 固定签名 | 接受并忽略新版多传的路由参数 |

## 实测（0.5.6 真机）

```
live_preview: True
seen: ['ThinkingEvent', 'ToolUseStartEvent', 'DoneEvent']
卡片：🧠 1 轮 · 🛠️ 2 个工具 · ⏳ 5.3 秒
     ✅ 已完成 · 5.3s · ⚕gemini-3.8-flash-high · 输入 640.0K 输出 8.2K 思考 1.9K · 80.0K/1.0M (7%)
```

## 升级

```bash
pip install --upgrade git+https://github.com/Duseus/opensquilla-lark-streaming.git@v0.1.2
osls install        # 升级 OpenSquilla 会覆盖 shim，必须重跑
systemctl --user restart opensquilla-gateway
```

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.1...v0.1.2
