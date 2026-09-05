---
name: agent-model-router
description: 当需要调用 Agent 并指定特定的 provider 路由或模型时使用此技能。从 ZCode 已配置的 provider 中选择，支持列出所有可用 provider、搜索模型、获取路由配置。适用于需要多模型协作、成本优化、或针对任务特性选择最佳模型的场景。当用户说"启动多个 agent"、"并行分析"、"选择模型"、"选择 provider"、"列出可用的 provider"、"有哪些 provider"、"可用的模型"时触发。
when_to_use: 用户想查看/选择 ZCode 中已配置的 provider 或模型时；用户要启动一个或多个并行 Agent 并希望为每个 Agent 指定不同 provider/模型时；涉及多模型协作、按任务分配模型、成本优化选型时。
---

# Agent Model Router

## Overview

从 ZCode 已配置的 provider 中选择 provider/模型，通过生成绑定模型的自定义子智能体（`~/.zcode/agents/` 定义文件），让每个子智能体真实运行在用户选定的模型上。

## 脚本位置（重要：先定位，再执行）

脚本是本 SKILL.md **所在目录**下 `scripts/` 子目录中的 `router.py`。

- 技能加载时上下文里已有本 SKILL.md 的绝对路径，`router.py` 的路径 = 该路径去掉文件名后拼接 `scripts/router.py`。
- **禁止凭记忆猜测安装目录层级**（不要在插件版本号目录和 `scripts` 之间凭空插入其他目录名）。
- 不确定时，先用文件搜索定位 `**/agent-model-router/scripts/router.py`，确认存在后再执行。

列出可用 provider（下文示例中的路径均指上面定位到的实际路径）：

```bash
python "<本技能目录>/scripts/router.py" list
```

## 如何搜索模型

```bash
python "<本技能目录>/scripts/router.py" search <关键词>
```

## 并行 Agent 时的 Provider 选择流程（真实模型路由）

> **🚨 硬性规定：当用户要求启动 Agent 时，禁止跳过以下选择流程。必须先完成步骤 1 → 2 → 3 的完整流程，获得用户明确选择的模型后，才能启动 Agent。不得直接用 general-purpose 或 Explore 启动，不得假设用户想要什么模型，不得跳过弹窗。**

**原理**：Agent 工具本身没有模型参数，在 prompt 文本里写"本 Agent 指定使用 provider X / 模型 Y"**没有任何效力**——子智能体只会按主会话默认模型运行（假路由，严禁这样糊弄用户）。ZCode 真实生效的方式是**自定义子智能体定义**：`~/.zcode/agents/<名称>.md` 的 frontmatter 里 `model` 字段绑定具体模型，Agent 工具用 `subagent_type` 选它，执行时就是绑定的那个模型。

**前置条件**：需要先执行 `/router-setup` 批量生成所有模型的定义文件（一次性操作）。如果没有执行过，步骤 1 会检测到并提示。

当用户要启动多个并行 Agent 时，**必须按以下流程执行，不得跳过任何步骤**：

### 步骤 1：获取可用 Provider 列表 + 检测定义

运行上面定位好的脚本 `list` 命令，获取当前可用的 provider 和模型。

同时检测 `~/.zcode/agents/router-*.md` 是否存在：
- **存在且数量合理**（≥1）：继续步骤 2
- **不存在或过少**：告知用户「尚未生成子智能体定义，请先执行 `/router-setup` 并新建会话后再使用本技能。」然后**停止**，不执行后续步骤。

### 步骤 2：选择 Provider 和模型

> **关键约束**：AskUserQuestion 最多 4 个选项，但可能有 13+ 个模型。必须用「文本列表 + 搜索 + 弹窗确认」组合方式。

**2a. 展示完整列表**

运行 `router.py list` 后，格式化为**带编号的文本列表**，直接输出给用户（不要试图塞进 AskUserQuestion）：

```
可用 Provider 和模型：
 1. 42w — claude-fable-5, gpt-5.4, gpt-5.4-mini, gpt-5.6-luna
 2. 121628 — deepseek-v4-flash-free
 3. xiaomimimo — mimo-v2.5-pro, mimo-v2.5
 4. amd — gemini-3.7-flash
 5. builtin:bigmodel — GLM-5.3, GLM-5.3-Flash, GLM-5-Turbo
 6. builtin:bigmodel-start-plan — GLM-5.3, GLM-5.3-Flash
 7. c83a8367 — DeepSeek-V4-Flash-Vision-Exp, Qwen3.8-Flash-Next
```

（以上为输出格式示例，实际内容以 `router.py list` 的输出为准。弹窗在下一步出现，用户通过弹窗或 Other 输入完成选择。）

**2b. 弹窗 + Other 输入**

输出文本列表后**立即**用 AskUserQuestion 弹窗（两者同轮进行，文本供参考，弹窗供选择）。

弹窗固定放 4 个快捷选项——**从步骤 1 实际获取的模型中挑选 4 个常用的**（不要硬编码示例中的模型名，以下仅为格式示例）：

- option 1: `<模型A>（<provider名>）`
- option 2: `<模型B>（<provider名>）`
- option 3: `<模型C>（<provider名>）`
- option 4: `<模型D>（<provider名>）`

Other 输入支持：
- **编号**（如 `2`）→ 显示该 provider 下所有模型，再弹一轮
- **关键词**（如 `deepseek`）→ 运行 `router.py search deepseek`，显示匹配结果
- **router-* 类型名**（如 `router-deepseek-v4-flash-free`）→ 直接使用

**2c. 搜索结果处理**

- **匹配 1 个** → 直接确认使用，不再弹窗
- **匹配 2-4 个** → AskUserQuestion 弹窗选择
- **匹配 >4 个** → 文本列表 + Other 输入，或让用户继续缩小关键词

**2d. 多 Agent 并行时**

每个 Agent **独立走一遍** 2a-2c 流程，逐个选择。不要一次性弹多个问题。

### 步骤 3：直接用已加载的 router-* 类型启动 Agent

弹框选完后，**不要运行 create-agent**（定义已通过 `/router-setup` 预先生成）。直接用 `subagent_type=router-<模型名>` 启动 Agent。

**智能检测**：如果启动时报 `Agent type not found`，说明该定义是本会话新建的、尚未被 ZCode 加载。此时：
1. 停止启动
2. 告知用户：「定义已存在但当前会话未加载，请**新建会话**后重新执行本技能。」
3. 不要用 general-purpose 替代，不要 fallback 到其他 router 类型。

## 快速命令

| 命令 | 说明 |
|------|------|
| `列出可用的 provider` | 显示所有可用 provider |
| `搜索 <关键词>` | 搜索模型 |
| `选择模型` | 弹出模型选择界面 |

## 注意事项

- 只能使用 ZCode 中已配置且已启用的 provider（`list` 输出中 ✅ 标记的）
- 并行 Agent 时，为每个 Agent 单独选择 provider 和模型
- **严禁假路由**：把"指定使用模型 X"写进子智能体 prompt 文本不产生任何效果；真实路由必须通过 `router-*` 子智能体类型实现
- **日常使用不需要 create-agent**——定义已通过 `/router-setup` 预先生成。直接用 `subagent_type=router-<模型名>` 启动
- 新增 provider 或模型后，需重新执行 `/router-setup` 并新建会话
- **启动子智能体时禁止使用 Explore 类型**——Explore 没有 AskUserQuestion 工具会导致弹框不出现（插件的 PreToolUse Hook 会强制拦截）
- 子智能体内部不能再派发子智能体，选择与创建的动作只能由主会话执行

## 🚫 禁止行为（硬性约束）

以下行为**严格禁止**，违反即为 bug：

1. **禁止跳过选择流程**：不得在未完成步骤 1→2→3 的情况下启动 Agent。即使用户直接说了任务描述（如"分析代码"），也必须先走完选择流程。
2. **禁止用 general-purpose 替代 router-***：general-purpose 使用主会话模型，不是真实路由。
3. **禁止假设用户想要什么模型**：必须通过 AskUserQuestion 或文本交互让用户明确选择。
4. **禁止在弹窗前启动 Agent**：Agent 只能在用户选择了模型之后启动，不能先启动再补选。
5. **禁止一次弹多个 AskUserQuestion**：每个 Agent 独立走一遍选择流程，逐个弹窗。
