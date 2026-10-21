# Changelog

## 0.1.7 — 2026-10-22

修复「内容早就说完了，卡片一直显示 💭 处理中」。

- **竞态**：`_load_footer`（后台取天气/一言）在封卡**之后**才返回，调 `_refresh_card(done=False)`
  把已经变绿的卡片又刷回「处理中」，且此后再无更新 → 看起来像卡死。
- `_refresh_card` 现在记录 `state["finished"]`（封卡成功后置位），并拒绝任何
  `done=False` 的迟到刷新；`_load_footer` 在封卡后直接跳过。
- 新增 `feishu.card_finished` 日志（card_id / chars / failed），收尾是否真的落地一眼可查。
- 实测：封卡后等 12s 复查，卡片仍是 ✅ 已完成，未回退。


## 0.1.6 — 2026-10-22

修复「一段流式卡片 + 一段纯文本」的截断式降级。

- **根因是 relay 的 10 秒收尾超时**：`relay.close()` 用
  `asyncio.wait_for(stream_task, timeout=10)` 等 `send_streaming` 收工。原来刷字是在
  chunk 循环里同步 `await` 的，而一次整卡 PUT / 刷字要 0.7–1s，长任务时我们根本来不及收尾
  → 超时被 cancel → 卡片停在 `💭 处理中`，剩余正文由 relay 用 `channel.send` 补成纯文本。
- 刷字改为**后台 coalescing worker**：chunk 循环只标记 dirty、立即返回；后台每
  `interval` 取最新全文刷一次，天然合并高频 delta。收尾前 `drain_pushes(3s)` 再封卡。
- 实测 120 段长文本：**最后一段到函数返回 0.9s**（阈值 10s），卡片完整 ✅ 已完成，
  `card_stream_fallback` / `streaming_card_failed` 计数 0。


## 0.1.5 — 2026-10-22

修复「长任务退化成纯文本、丢卡片」。

- **实时预览开关没打开**：0.5.x 的 `_channel_can_replace_streamed_text()` 要求
  `capability_profile.streamed_message_replacement=True`，原生 Feishu 只声明了 `edit=True`
  → `live_preview=False` → relay 把所有 delta 攒到 Done 才一次性交付，长任务动辄几千字，
  最终只落一条大消息（或干脆没建卡，直接走 `channel.send` 发纯文本）。
- `apply()` 现在覆写 `capability_profile`，在原生 profile 上补
  `streamed_message_replacement=True`（我们的 `send_streaming` 确实返回稳定消息 id，
  `edit` 也已支持卡片，声明属实）。
- 增加排障日志：`feishu.card_created` / `feishu.card_edit_reconcile` /
  `feishu.card_stream_fallback` / `feishu.streaming_card_failed`。
- 实测：`live_preview: True`、`policy: adapter_stream`，长文本流式 + 收尾 edit 正常。


## 0.1.4 — 2026-10-21

修复「任务一长卡片就没了 / 卡片外加一大段纯文本」。

- **刷字接口路径错了**：CardKit 流式刷字是
  `PUT /cardkit/v1/cards/{id}/elements/{eid}/content/content`（两个 `content`），
  且要带 `uuid` 幂等键；旧代码打到 `/elements/{eid}/content`，稳定 400
  `element is required`。失败会一路冒泡出去，卡片停在半截。
- **收尾 `edit` 打到了错误对象**：relay 用 `channel.edit(message_id, text)` 覆盖流式消息，
  但我们的 message_id 是卡片消息，`FeishuChannel.edit` 按文本消息处理必然 400；
  relay 判定替换失败后会把**整段答案重发成纯文本**。现在 `edit` 命中卡片时改走整卡更新。
- 刷字失败自动退回整卡 PUT（实测 75KB 无压力），不会再把卡片打断。
- 实测：40 段长文本流式 → 卡片持续更新、`edit` 收尾成功、最终 ✅ 已完成。

## 0.1.3 — 2026-10-21

修复 OpenSquilla 0.5.6 上升级后「只发纯文本、不出卡片」。

- 0.5.x 的 `FeishuChannel.STREAM_UPDATE_STRATEGY = "final_only"` 会让 relay 完全跳过
  流式通道（`relay_stream=False`，只调用 `channel.send`）。`apply()` 现在运行期覆盖为
  `adapter_stream`；0.3.x 时代这一行是直接改源码的常量，改 shim 后必须显式设置。
- 实测：`resolve_channel_stream_policy(FeishuChannel)` 由 `final_only` 变为
  `adapter_stream`，`relay_stream=True`。

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
