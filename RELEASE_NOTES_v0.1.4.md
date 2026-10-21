# v0.1.4 — 长任务不再掉卡片

## 症状

短问题正常出卡片；任务一长（多轮工具、长答案），卡片停在半截或者干脆看不到，回复变成一两条纯文本消息。

## 两个根因（都在流式链路上）

### 1. 刷字接口打错路径

CardKit 的「文本流式更新」接口是：

```
PUT /open-apis/cardkit/v1/cards/{card_id}/elements/{element_id}/content/content
```

注意**两个 `content`**，并且要带幂等键 `uuid`，卡片还得 `config.streaming_mode = true`。

旧代码打到 `/elements/{element_id}/content`（单个 content），Feishu 返回：

```
400 code=99992402 field validation failed
field_violations: [{"field": "element", "description": "element is required"}]
```

流式刷字一抛异常，卡片就停在半截。

实测正确路径：1000 / 5000 / 12000 字全部 `code:0 success`。

### 2. 收尾 `edit` 打在卡片消息上

turn 结束后 relay 会调用 `channel.edit(handle.message_id, canonical_text)` 用最终文本覆盖流式消息。
我们的 `message_id` 是卡片消息，`FeishuChannel.edit` 按文本消息处理 → 400 →
relay 判定「替换失败」，走 fallback 把**整段答案重发成纯文本**。

现在 `apply()` 覆写 `edit`：命中卡片 id 就改走整卡更新（并把状态标记完成），只有普通文本消息才交给原生实现。

## 兜底

刷字失败自动退回整卡 `PUT /cardkit/v1/cards/{id}`——实测单卡 75KB 仍成功，不会再把卡片打断。

## 实测

```
send_streaming -> om_x100b62ba67d3b0a0dea498f9010869c   # 40 段长文本
edit ok
卡片：✅ 已完成 · 31.1s  （内容为流式累积结果，收尾 edit 成功覆盖）
```

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.3...v0.1.4
