# OpenSquilla Lark Streaming v0.1.9

## 🔍 处理中过程可视化（展开面板 + 详细工具参数）

修复处理中折叠面板默认闭合导致用户看不见思考过程与工具调用明细的问题。

### 核心改进

1. **处理中面板默认自动展开**：
   - `collapsible_panel` 的 `expanded` 属性在流式生成中（`done=False`）保持 `True`，无需用户每次手动点击展开按钮，思考过程和正在执行的工具步骤实时可见。
   - 封卡完成时（`done=True`）自动折叠收起，保证最终输出卡片紧凑干净。

2. **完整捕获工具入参明细 (`tool_use_end`)**：
   - 增加对 `ToolUseEndEvent` 的监听与解析，提取执行的完整 `arguments`，正确渲染具体命令（如 `git status`、`ls`、查询关键词）。
