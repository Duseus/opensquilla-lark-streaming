# v0.1.1 — 面板详细度上调

回应「展示的东西要详细一点点」：折叠面板里的思考内容不再压成一句摘要。

## 变化

| 项 | v0.1.0 | v0.1.1 |
|---|---|---|
| 每轮思考原文保留 | 400 字 | **4000 字** |
| 卡片内展示 | 200 字，压成单行 | **1200 字，保留换行分段** |
| 工具行 / 底栏 | — | 不变 |

## 效果

```
▶ 🧠 3 轮 · 🛠️ 3 个工具 · ⏳ 5.3 秒
    第 1 轮 · 0.4s
    用户报的是卡片没有工具过程。先确认运行时是不是 OpenSquilla，
    再看 channels/feishu.py 里的 STREAM_UPDATE_STRATEGY。如果还是
    final_only，说明 gateway 根本没启动 relay，补丁再漂亮也不会被调用。
    确认后要检查 note_stream_event 有没有接上 tool_use_start /
    tool_result，这两个事件默认只给 web 端用，通道侧拿不到。
    Run command (352 ms)
    journalctl --since "2026-10-21 16:51" | grep -i context
```

## 升级

```bash
pip install --upgrade git+https://github.com/Duseus/opensquilla-lark-streaming.git@v0.1.1
osls install
systemctl --user restart opensquilla-gateway
```

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.0...v0.1.1
