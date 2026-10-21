# OpenSquilla Lark Streaming

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenSquilla](https://img.shields.io/badge/OpenSquilla-%E2%89%A50.3.0-6f42c1)](https://pypi.org/project/opensquilla/)

给 [OpenSquilla](https://pypi.org/project/opensquilla/) 的飞书（Lark）通道做**流式卡片**：一条消息里边想边写，工具调用过程、轮次耗时、token 与上下文占用全在卡片里，完成时整卡变绿。

> 效果对标 Hermes 的 `hermes-lark-streaming`，但代码零依赖、只依赖飞书 CardKit 2.0 原生 API。

[English](README.en.md)

---

## 卡片长这样

```
┌──────────────────────────────────────────────────┐
│  💭 Tanuki 处理中…                       (蓝色)  │
│                                                  │
│  节点掉线的根因是 DNS 缓存过期，我先把 keepalive  │
│  脚本跑一遍，再对照日志确认。                    │
│                                                  │
│  ▶ 🧠 5 轮 · 🛠️ 8 个工具 · ⏳ 9.7 秒             │
│      第 1 轮 · 0.7s                              │
│      先看节点清单和 keepalive 脚本。             │
│      Run command (352 ms)                        │
│      bash instabox_fleet_keepalive.sh            │
│      Read (20 ms)                                │
│      instabox_fleet_keepalive.sh                 │
│      第 2 轮 · 0.5s                              │
│      …                                           │
│  ────────────────────────────────────────────    │
│  ✅ 已完成 · 4m 11s · ⚕gemini-3.8-flash-high     │
│  输入 10.0M 输出 18.0K 思考 4.4K · 159.9K/1.0M (15%) │
│  ☀️ 临平 20.6°C/14.3°C · 湿度 76%                │
│  💬 「保持好奇，持续折腾。」                     │
└──────────────────────────────────────────────────┘
```

- **蓝色 = 流式中**，**绿色 = 完成**，**红色 = 中止**
- 折叠面板点开就是完整过程，**不截断**（150 个元素以内全量渲染）
- 每个工具一行 `Run command (201 ms)` + 真实命令/文件/查询词

---

## 功能

| 能力 | 说明 |
|---|---|
| 流式正文 | CardKit `streaming_mode` + 元素级增量更新，打字机效果 |
| 轮次面板 | 按「思考 → 工具 → 再思考」自动切轮，每轮带耗时 |
| 工具明细 | 命令、文件、搜索词一行展示，工具名自动翻译成人类可读标题 |
| 状态色 | header 蓝→绿/红，一眼看出跑没跑完 |
| token 指标 | 输入 / 输出 / 思考，自动 K/M 紧凑化 |
| 上下文占用 | `159.9K/1.0M (15%)`，模型窗口自动解析 |
| 天气 + 一言 | open-meteo + hitokoto，纯标准库，取不到就静默降级 |
| 降级 | 建卡失败自动回退成普通文本消息，不吞回复 |

---

## 运行要求

- OpenSquilla `>= 0.3.0`（已装好飞书通道并连通）
- Python `>= 3.10`
- 飞书应用权限：
  - `im:message`（发消息）
  - `cardkit:card:write`（创建/更新卡片）
- 无需额外 Python 依赖（`httpx` 由 OpenSquilla 自带）

---

## 安装

```bash
pip install opensquilla-lark-streaming

osls status     # 看是否找到 OpenSquilla 与当前注入状态
osls install    # 注入 shim（自动备份原文件）
systemctl --user restart opensquilla-gateway
```

`osls install` 只往 `opensquilla/channels/feishu.py` 末尾追加 6 行 shim：

```python
# >>> opensquilla-lark-streaming shim (managed) >>>
try:
    from opensquilla_lark_streaming import patch as _osls_patch

    _osls_patch.apply(FeishuChannel)
except Exception as _osls_exc:
    ...
# <<< opensquilla-lark-streaming shim <<<
```

卸载：

```bash
osls uninstall && systemctl --user restart opensquilla-gateway
```

详细步骤见 [INSTALL.md](INSTALL.md)。

---

## 原理

```
OpenSquilla gateway
      │  事件流（thinking / tool_use_start / tool_result / router_decision / done）
      ▼
channel_dispatch._RuntimeChannelStreamRelay
      │  note_stream_event(event)
      ▼
FeishuChannel ──► build_card() ──► 飞书 CardKit
                     │
                     ├─ header：状态 + 颜色
                     ├─ markdown(content)：流式正文
                     ├─ collapsible_panel：轮次 / 工具 / 明细
                     └─ footer：耗时 · 模型 · token · 上下文 · 天气 · 一言
```

本包**不改 OpenSquilla 源码逻辑**，只用 `patch.apply(FeishuChannel)` 在运行时给类挂方法：

| 方法 | 职责 |
|---|---|
| `send_streaming` | 建卡 → 增量刷字 → 封卡；异常时回退普通消息 |
| `note_stream_event` | 把事件折叠进 `rounds` / `tools` / `usage` |
| `_cardkit_*` | 建卡、更新元素、结束卡片 |

同时给 `channel_dispatch` 补一个 `done` 事件转发（OpenSquilla 默认只转发思考与工具事件），否则拿不到 token 数。

---

## 配置

想改「谁在说话」、天气位置、一言分类，直接改源码常量后重启：

| 位置 | 变量 | 默认 |
|---|---|---|
| `patch.py` / `build_card` | `agent_name` | `Tanuki` |
| `metrics.py` | `WEATHER_LATITUDE` / `WEATHER_LONGITUDE` / `WEATHER_PLACE` | 杭州临平 30.42 / 120.30 |
| `metrics.py` | `HITOKOTO_FALLBACK` | 4 条兜底句子 |
| `card.py` | `MAX_PANEL_ELEMENTS` / `KEEP_PANEL_ELEMENTS` | 150 / 140 |

---

## 已知取舍

1. **上下文占用是估算值**：OpenSquilla 的 `DoneEvent` 只给本轮累计 token，没有当前上下文长度，所以按 `输入 ÷ 迭代次数` 折算。要精确值需要接 session 的 `context_tokens`。
2. **升级 OpenSquilla 会覆盖 shim**：`pip install --upgrade opensquilla` 之后重跑 `osls install`。
3. **卡片元素上限**：飞书单卡约 200 元素，超过 150 时保留最近 140 项并提示「还有 N 项已折叠（超出卡片上限）」。

---

## 开发

```bash
git clone https://github.com/Duseus/opensquilla-lark-streaming
cd opensquilla-lark-streaming
python -m pip install -e ".[dev]"
pytest -q          # 纯函数单测，不需要 OpenSquilla
```

目录：

```
src/opensquilla_lark_streaming/
├── card.py         # 卡片 JSON 构建（纯函数）
├── descriptors.py  # 工具名 → 标题/图标/明细
├── metrics.py      # 数字格式化、天气、一言、上下文窗口
├── patch.py        # 运行时给 FeishuChannel 挂方法
├── installer.py    # shim 注入 / 移除 / 状态
└── cli.py          # osls 命令
```

##  License

MIT © Duseus
