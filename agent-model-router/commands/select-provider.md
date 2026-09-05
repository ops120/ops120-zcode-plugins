---
description: 启动 Agent 前选择 provider 和模型
---

先用 Skill 工具加载 `agent-model-router` 技能，然后严格按照技能中"并行 Agent 时的 Provider 选择流程"执行：

1. 运行技能目录下的 `scripts/router.py list` 获取可用 provider 列表（脚本路径以技能加载后提示的 SKILL.md 所在目录为准）。
2. 将结果格式化为带编号的文本列表（provider ID + 模型名），直接输出给用户。
3. 用 AskUserQuestion 弹窗提供 4 个常用模型作为快捷选项，用户也可通过 Other 输入编号、关键词或 router-* 类型名。
4. 搜索结果 ≤4 个 → 弹窗选择；>4 个 → 文本列表 + Other；1 个 → 直接确认。
5. 等用户选择后，用 `subagent_type=router-<模型名>` 启动 Agent（禁止使用 general-purpose 或 Explore）。

任务参数：$ARGUMENTS
