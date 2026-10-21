# v0.1.7 — 内容说完了，状态还挂在「处理中」

## 症状

卡片正文已经写满、底栏时间也停在 18.1s，标题却一直是 `💭 Tanuki 处理中...`，永远不变绿。

## 根因：封卡之后被后台刷新刷回去了

`send_streaming` 里有两路写卡：

1. 主流程：`_cardkit_finish()` → `_refresh_card(done=True)` → 标题 `✅ 已完成`；
2. 后台：`_load_footer()` 去取天气/一言（网络请求，几百毫秒到几秒），拿到后调
   `_refresh_card(done=False)` 再刷一次。

两者没有先后约束。footer 慢的时候，它的 `done=False` 刷新**落在封卡之后**，于是把绿色的
`✅ 已完成` 又写回 `💭 处理中`。此后没有任何事件再刷卡 —— 用户看到的就是「内容说完了，状态还
在处理中」。

日志特征：`feishu.card_created` → 一串刷字 → 没有 `feishu.card_finished`，
最后一条 PUT 的底栏是 `💭 处理中 · 18.1s`。

## 修复

```python
# 封卡成功 → 置 finished
if done:
    state["finished"] = True

# 迟到刷新直接丢弃
if state.get("finished") and not done:
    return
```

`_load_footer` 同样在封卡后跳过刷新。新增 `feishu.card_finished` 日志，
带上 `card_id / chars / failed`，收尾是否真的落地一眼可查。

## 实测

```
feishu.card_finished card_id=7699208946544282929 chars=1812 failed=False
总耗时 12.7s，最后一段到返回 1.2s
封卡后等待 12s 复查：标题仍是 ✅ 已完成，底栏 ✅ 已完成 · 12.1s
```

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.6...v0.1.7
