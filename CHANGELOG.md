# Changelog

## 0.1.2 — 2026-10-21

兼容 OpenSquilla 0.5.6（0.3.x 仍可用）。

- 0.5.x 的 `_RuntimeChannelStreamRelay` 不再有 `_forward_tool_event`，改为覆写
  `relay.emit(event)` 把思考/工具/Done 事件转发给通道
- 强制 `relay._live_preview = True`：0.5.x 默认把正文攒到 Done 才交付，否则卡片没有打字效果
- `send_streaming` 接受并忽略新版多传的路由参数（`**kwargs`）
- 在 0.5.6 上实测：`live_preview=True`，`ThinkingEvent / ToolUseStartEvent / DoneEvent` 全部到达通道

## 0.1.1 — 2026-10-21

面板详细度上调（用户反馈「展示的东西要详细一点点」）。

- 每轮思考原文保留上限 `400 字 → 4000 字`
- 卡片内预览 `200 字 → 1200 字`，并且**保留换行/分段**（之前压成单行）
- 工具行与底栏不变

## 0.1.0 — 2026-10-21

首个公开版本，把内部在 OpenSquilla 0.3.0 上跑通的流式卡片整理成可安装的包。

- CardKit 2.0 流式卡片：蓝色流式 → 绿色完成 / 红色中止
- 思考轮次分面板：每轮带耗时，思考内容取前 200 字预览
- 工具步骤：人类可读标题 + 耗时（`Run command (201 ms)`）+ 命令/文件/查询明细
- 底栏指标：`✅ 已完成 · 4m 11s · ⚕model · 输入 X 输出 Y 思考 Z · 159.9K/1.0M (15%)`
- 天气（open-meteo）与一言（hitokoto），失败静默降级
- 面板 150 元素内全量渲染，超限才裁剪并提示
- `osls install / uninstall / status` 安装器，改前自动备份
