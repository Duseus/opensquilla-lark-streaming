# v0.1.6 — 修掉「一段卡片 + 一段文本」的截断降级

## 症状

长任务回复被劈成两半：前面一段在流式卡片里，后面一段变成两条纯文本消息，卡片永远停在 `💭 处理中`。

## 根因：relay 的 10 秒收尾超时被我们撞穿

`_RuntimeChannelStreamRelay.close()`：

```python
self._stream_handle = await asyncio.wait_for(
    asyncio.shield(self._task), timeout=timeout   # timeout=10.0
)
...
if self.stream_error is not None:
    fallback_text = undelivered_yielded + "".join(queued_remainder)
    await self._channel.send(_build_reply_message(...))   # ← 你看到的那两条文本
```

原来 `send_streaming` 的刷字是在 chunk 循环里**同步 await**：

```python
if now - last_push >= interval_s:
    await push_content(accumulated)   # 一次整卡 PUT / 刷字 ≈ 0.7~1s
```

长任务时正文来得快、刷字又慢，模型说完了我们还在排队刷 → 10 秒超时 → `stream_task.cancel()`
→ 卡片停在半截（连完成态都来不及写），relay 把「没交付的部分」用 `channel.send` 补成纯文本。

日志特征：`feishu.card_created` 之后是一串 `feishu.card_stream_fallback`，然后两条
`feishu.reply`，从头到尾没有 `card_finished`。

## 修复

刷字从「同步 await」改成「后台合并刷」：

```python
push_bg = {"task": None, "dirty": False}

def push_content(content):          # chunk 循环里调用，零阻塞
    push_bg["dirty"] = True
    if task is None or task.done():
        push_bg["task"] = asyncio.create_task(push_loop())

async def push_loop():              # 每 interval 取最新全文刷一次，天然合并 delta
    while push_bg["dirty"]:
        push_bg["dirty"] = False
        await push_once()
        await asyncio.sleep(interval_s)
```

收尾前 `drain_pushes(3s)`，然后写完成态封卡。

## 实测

120 段长文本（每段间隔 80ms）：

```
feishu.card_created card_id=7699159313445408008 chars=14
total=13.4s  after_last_chunk=0.9s     # 阈值 10s，余量 11 倍
卡片：✅ 已完成 · 12.8s，120 段完整
card_stream_fallback / streaming_card_failed 计数 0
```

## 顺带结论

CardKit 的 `/elements/{id}/content/content`（元素级流式刷字）在本租户上会间歇性返回
`404 page not found`，不可靠；整卡 PUT 实测 75KB 稳定，因此刷字统一走整卡 PUT。

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.5...v0.1.6
