# v0.1.0 — 首个公开版本

给 OpenSquilla 的飞书通道加流式卡片：一条消息里边想边写，完成变绿，工具过程可展开。

## 亮点

- **CardKit 2.0 流式卡片** —— 蓝色流式 → 绿色完成 / 红色中止，元素级增量更新
- **轮次面板** —— 按「思考 → 工具 → 再思考」自动分轮，每轮带耗时；思考内容取预览
- **工具步骤** —— 人类可读标题 + 耗时（`Run command (201 ms)`），下一行给真实命令 / 文件 / 查询词
- **底栏指标** —— `✅ 已完成 · 4m 11s · ⚕model · 输入 10.0M 输出 18.0K 思考 4.4K · 159.9K/1.0M (15%)`
- **天气 + 一言** —— open-meteo 与 hitokoto，纯标准库，失败静默降级
- **不偷偷截断** —— 面板 150 元素内全量渲染，点开就能看到每一步
- **装得干净** —— `osls install` 只往 `channels/feishu.py` 追加 6 行 shim，改前自动备份，`osls uninstall` 可完整回滚

## 安装

```bash
pip install git+https://github.com/Duseus/opensquilla-lark-streaming.git@v0.1.0
osls install
systemctl --user restart opensquilla-gateway
```

装完在飞书里 @ 机器人问一句即可看到效果。

## 已验证环境

| 项 | 值 |
|---|---|
| OpenSquilla | 0.3.0 |
| Python | 3.13 |
| 飞书 SDK | lark-oapi 1.7.5（包本身零额外依赖） |
| 单测 | 22 passed（`pytest -q`，纯函数，无需 OpenSquilla） |
| 实机 | 在 OpenSquilla 0.3.0 上真实建卡 / 刷字 / 封卡通过 |

## 已知取舍

1. **上下文占用是估算**：`DoneEvent` 只给本轮累计 token，按 `输入 ÷ 迭代次数` 折算；需要精确值要接 session 的 `context_tokens`。
2. **升级 OpenSquilla 会覆盖 shim**：`pip install --upgrade opensquilla` 后重跑 `osls install`。

## 变更

- 首个版本，包含 `card.py` / `descriptors.py` / `metrics.py` / `patch.py` / `installer.py` / `cli.py`
- 22 个单测覆盖卡片结构、工具描述符、指标格式化、折叠策略

**Full Changelog**: https://github.com/Duseus/opensquilla-lark-streaming/commits/v0.1.0
