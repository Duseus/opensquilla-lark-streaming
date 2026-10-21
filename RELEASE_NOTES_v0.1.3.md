# v0.1.3 — 修复 OpenSquilla 0.5.6 上「只发纯文本、不出卡片」

## 症状

升级到 0.5.6 后机器人能回复，但回复是**纯文本消息**，没有流式卡片；日志里连一条
`cardkit` / `send_streaming` 记录都没有。

## 根因

0.5.x 的 `FeishuChannel` 显式声明了：

```python
STREAM_UPDATE_STRATEGY = "final_only"
```

`opensquilla.channels.stream_policy.resolve_channel_stream_policy()` 看到这个覆盖值就直接
返回 `final_only`（`relay_stream=False`），relay 于是绕过 `send_streaming`，走
`channel.send()` 发纯文本。

0.3.x 时代这一行是**直接改 site-packages 源码**改掉的；改用 shim 注入后没人动这个常量，
于是卡片静默失效。

## 修复

`apply()` 里运行期覆盖：

```python
channel_cls.STREAM_UPDATE_STRATEGY = "adapter_stream"
channel_cls.stream_update_strategy = "adapter_stream"
```

## 实测

```
policy before: adapter_stream   # 挂上 shim 后
policy after : adapter_stream relay_stream= True
```

`osls install` 后重启 gateway 即生效。

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/compare/v0.1.2...v0.1.3
