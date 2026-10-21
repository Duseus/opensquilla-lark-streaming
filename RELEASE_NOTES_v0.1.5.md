# v0.1.5 — 长任务不再退化成纯文本

## 症状

短问答出卡片；任务一长就"退化"：要么卡片停在 `💭 处理中` 不动、后面跟一两条纯文本，要么整条回复就是纯文本。

## 根因：实时预览开关（live_preview）没打开

OpenSquilla 0.5.x 判定要不要实时预览：

```python
def _channel_can_replace_streamed_text(channel) -> bool:
    if resolve_channel_stream_policy(channel).mode == "final_only":
        return False
    profile = channel_capability_profile(channel)
    return bool(profile.edit and profile.streamed_message_replacement and has_edit)
```

原生 `FeishuChannel.capability_profile` 只声明了 `edit=True`，**没有** `streamed_message_replacement`，
所以 `live_preview=False`：

- 所有 `TextDeltaEvent` 都不进流式队列，只在 `Done` 后一次性把全文丢给 `send_streaming`；
- 长任务几千字 → 单条巨量文本；Done 快照缺失/为空时连卡都不建，直接 `channel.send()` 发纯文本。

这跟 0.3.x 的行为不同：那时候没有这个 capability 判定，所以补丁能直接流。

## 修复

`apply()` 覆写 `capability_profile`，在原生 profile 上补：

```python
dataclasses.replace(profile, streamed_message_replacement=True)
```

依据是事实：我们的 `send_streaming` 返回稳定的消息 id，`edit` 已能更新卡片（v0.1.4 修的就是这条路径），
所以这个能力声明是诚实的，不是硬开。

## 实测

```
streamed_message_replacement: True edit: True
policy: adapter_stream
live_preview: True
```

长文本流式：`feishu.card_created` → `feishu.card_edit_reconcile chars=205` → 卡片 ✅ 已完成，
`card_stream_fallback` / `streaming_card_failed` 计数 0。

## 新增排障日志

| 事件 | 含义 |
|---|---|
| `feishu.card_created` | 建卡成功（带字符数）|
| `feishu.card_edit_reconcile` | 收尾 edit 命中卡片并更新 |
| `feishu.card_stream_fallback` | 流式刷字失败，退回整卡 PUT |
| `feishu.streaming_card_failed` | 整条流式链路失败，退回普通消息 |

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.4...v0.1.5
