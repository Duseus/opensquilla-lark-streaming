# OpenSquilla Lark Streaming v0.2.0

## 💎 Hermes / aiduPOP 水晶泡波全量对齐版

将我们在 Hermes Agent（aiduPOP）上打磨成熟的流式体验与工业级防护全量迁移至 OpenSquilla：

### 核心特性

1. **15ms 极速打字机韵律（Print Strategy Fast）**：
   - 注入 CardKit 2.0 官方流式配置：`print_strategy: "fast"`, `print_frequency_ms: 15`, `print_step: 1`。
   - 彻底告别大块刷新与机械顿挫，正文如电影字幕般行云流水逐字呈现。

2. **泡波（Bubble-Wave）灵动视觉体系**：
   - 引入完整 `theme.py` 主题层；
   - 统一面板统计行：`🌊 思考轮次 · 🫧 工具步骤 · ✨ 执行耗时`；
   - 拟人化 Emoji 工具图集：`👩🏻‍💻 Run command`、`👩🏻‍🏫 Read`、`👩🏻‍🎨 Edit`、`🕵🏻‍♀️ Search` 等；
   - 动态思考轮次标记：`🌊 第 N 轮`（橙色运行中，绿色完成）；
   - 展开状态：流式处理中默认自动展开，任务结束自动折叠；
   - 折叠溢出提示：`💦 还有 N 项已折叠`。

3. **Aegis 工业级内容防爆与字节安全**：
   - 引入 `md.py` 防爆引擎，采用 `clamp_utf8` 按 UTF-8 真实字节严格钳制卡片内容；
   - 根治中文 3 字节膨胀导致的飞书卡片 JSON 超限（30KB 硬限）溢出断屏；
   - 封卡完成态采用「首尾双保」（前 60% 背景背景 + 后 40% 核心结论，中段省略），超长任务不爆卡且核心结论永不丢失。
