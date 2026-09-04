---
name: agent-model-router
description: 当需要调用 Agent 并指定特定的 provider 路由或模型时使用此技能。从 ZCode 已配置的 provider 中选择，支持列出所有可用 provider、搜索模型、获取路由配置。适用于需要多模型协作、成本优化、或针对任务特性选择最佳模型的场景。当用户说"启动多个 agent"、"并行分析"、"选择模型"、"选择 provider"、"列出可用的 provider"、"有哪些 provider"、"可用的模型"时触发。
when_to_use: 用户想查看/选择 ZCode 中已配置的 provider 或模型时；用户要启动一个或多个并行 Agent 并希望为每个 Agent 指定不同 provider/模型时；涉及多模型协作、按任务分配模型、成本优化选型时。
---

# Agent Model Router

## Overview

从 ZCode 已配置的 provider 中选择路由，调用 Agent 时指定不同的 provider 和模型。

## 如何获取可用 Provider

运行此技能目录下的 `scripts/router.py` 脚本：

```bash
python scripts/router.py list
```

脚本位于本技能的 `scripts/` 子目录中。使用 Bash 工具执行时，路径为本 SKILL.md 所在目录下的 `scripts/router.py`。

## 如何搜索模型

```bash
python scripts/router.py search <关键词>
```

## 并行 Agent 时的 Provider 选择流程

当用户要启动多个并行 Agent 时，**必须**按以下流程执行：

### 步骤 1：获取可用 Provider 列表

运行脚本获取当前可用的 provider 和模型。

### 步骤 2：弹出选择界面

使用 `AskUserQuestion` 工具为每个 Agent 让用户选择 provider 和模型。

### 步骤 3：使用选择结果启动 Agent

根据用户选择，启动 Agent 时在 prompt 中指定 provider 和模型。

## 快速命令

| 命令 | 说明 |
|------|------|
| `列出可用的 provider` | 显示所有可用 provider |
| `搜索 <关键词>` | 搜索模型 |
| `选择模型` | 弹出模型选择界面 |

## 注意事项

- 只能使用 ZCode 中已配置且已启用的 provider
- 使用 `list` 命令查看哪些 provider 可用（✅ 标记）
- 并行 Agent 时，为每个 Agent 单独选择 provider 和模型
- **启动子智能体时必须使用 general-purpose 类型，禁止使用 Explore 类型**——Explore 类型没有 AskUserQuestion 工具，会导致弹框不出现
