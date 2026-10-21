# 安装指南

## 0. 前置检查

```bash
python -c "import opensquilla, importlib.metadata as m; print(m.version('opensquilla'))"
systemctl --user status opensquilla-gateway | head -5
```

要求：

- OpenSquilla `>= 0.3.0`，飞书通道已连通（日志里有 `gateway.channel_started channel=feishu`）
- 飞书应用已开通 `im:message`、`cardkit:card:write` 权限

验证 CardKit 权限（可选，能建卡就行）：

```bash
python - <<'EOF'
import json, urllib.request
app_id, app_secret = "cli_xxx", "xxx"
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"},
)
token = json.load(urllib.request.urlopen(req))["tenant_access_token"]
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/cardkit/v1/cards",
    data=json.dumps({"type": "card_json", "data": "{\"schema\":\"2.0\",\"body\":{\"elements\":[]}}"}}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
)
print(json.load(urllib.request.urlopen(req)))
EOF
```

返回 `code: 0` 即权限 OK。

## 1. 安装包

```bash
# 从 PyPI（发布后）
pip install opensquilla-lark-streaming

# 或从源码
git clone https://github.com/Duseus/opensquilla-lark-streaming
cd opensquilla-lark-streaming
pip install .
```

注意：请装在 **OpenSquilla 同一个 Python 环境**里（通常是它的 venv）：

```bash
/data/workspace/.venv/bin/pip install opensquilla-lark-streaming
```

## 2. 注入

```bash
/data/workspace/.venv/bin/osls status
/data/workspace/.venv/bin/osls install
```

输出示例：

```
已注入流式卡片 shim
备份文件: /data/workspace/.venv/lib/python3.13/site-packages/opensquilla/channels/feishu.py.bak-osls-1792589200
重启 gateway 后生效：systemctl --user restart opensquilla-gateway
```

## 3. 重启并验证

```bash
systemctl --user restart opensquilla-gateway
journalctl --user -u opensquilla-gateway -n 30 --no-pager | grep -i "channel_started\|feishu"
```

在飞书里 @ 机器人问一句，应该看到：

1. 先出现蓝色卡片，正文逐字增长；
2. 底部折叠面板出现轮次和工具；
3. 完成后 header 变绿，底栏出现 `✅ 已完成 · 耗时 · 模型 · token · 上下文`。

## 4. 常见问题

**卡片没出现，还是普通文本？**
看日志：

```bash
journalctl --user -u opensquilla-gateway -n 100 --no-pager | grep -i "cardkit\|streaming_card_failed"
```

- `cardkit create returned no card_id` → 应用没开 `cardkit:card:write`
- `sequence number compare failed` → 卡片更新序号冲突，重启 gateway
- `Invalid parameter type in json: Settings` → 老版本代码，升级到本包最新版

**升级 OpenSquilla 后失效？**

```bash
/data/workspace/.venv/bin/osls install && systemctl --user restart opensquilla-gateway
```

**想彻底回滚？**

```bash
/data/workspace/.venv/bin/osls uninstall
# 或从备份恢复
cp .../feishu.py.bak-osls-<ts> .../feishu.py
```
