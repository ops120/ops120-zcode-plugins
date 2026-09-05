# agent-model-router — 产品需求文档

> 版本：0.2.0 | 日期：2026-09-05

---

## 一、问题背景

### 痛点

当你在 ZCode 中启动多个 Agent（如并行分析代码、文档、架构），默认情况下所有 Agent 使用主会话的同一个模型。这导致：

- **成本浪费**：简单任务也被迫使用昂贵的大模型
- **能力单一**：无法让擅长代码的模型做代码任务、擅长写作的模型做文档任务
- **缺乏控制**：用户无法按任务特性选择合适的模型

### ZCode 的限制

ZCode 的 Agent 工具本身**不接受模型参数**。在派发提示词里写"本 Agent 使用 XX 模型"不会产生任何效果，子智能体始终沿用主会话模型（**假路由**）。

---

## 二、核心设计思路

### 真实路由的唯一途径

经过系统性探测（slash 格式 → 拒绝、裸模型名 → 路由到错误 provider），最终确认：

> **ZCode 的自定义子智能体机制是唯一能真实切换模型的途径。**

具体机制：

```
~/.zcode/agents/<name>.md  定义文件
    ↓
frontmatter 的 model 字段绑定具体模型
    ↓
主 Agent 以 subagent_type=<name> 启动
    ↓
ZCode 按定义文件加载模型 → 子智能体真实运行在指定模型上
```

### model 字段格式

```
custom:<provider_id>:<model_name>
```

| 组成部分 | 来源 | 示例 |
|----------|------|------|
| `custom:` | 固定前缀 | — |
| `<provider_id>` | `config.json` → `provider` 的 key | `121628`、`42w`、`builtin:bigmodel` |
| `<model_name>` | provider 下 `models` 的 key | `deepseek-v4-flash-free`、`gpt-5.4` |

错误格式及后果：

| 格式 | 结果 |
|------|------|
| `builtin:bigmodel-start-plan/GLM-5.3-Flash`（slash） | ZCode 拒绝，无 API 调用 |
| `GLM-5.3-Flash`（裸名） | 路由到错误的 provider |
| `custom:121628:deepseek-v4-flash-free`（正确） | 正常工作 |

---

## 三、热重载问题与架构决策

### 约束条件

ZCode 的子智能体定义**仅在会话启动时加载**，已启动的会话不会热更新。没有 API 或 CLI 可以强制重载。

这意味着：**在当前会话中生成的 `router-*.md` 定义，当前会话无法使用。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 每次用时动态生成 | 无需预生成 | 生成后必须新建会话才能用，体验极差 |
| B. 预生成 + 智能检测 | 日常使用零创建、零等待 | 首次需运行一次 setup |
| C. 要求用户手动创建定义 | 无 | 用户体验为零，不可行 |

**选择方案 B**：拆分为两个技能。

```
/router-setup        → 批量预生成所有 router-*.md（一次性，新增模型后重跑）
/agent-model-router  → 日常使用，直接启动（零创建）
```

### 两技能交互流程

```
                    ┌──────────────────────────────────────┐
                    │  /router-setup（一次性）              │
                    │  读取 config.json                     │
                    │  遍历所有 provider/model              │
                    │  批量生成 router-*.md                  │
                    └──────────────┬───────────────────────┘
                                   │
                                   v
                        "新建会话后生效"
                                   │
                    ┌──────────────┴───────────────────────┐
                    │  /agent-model-router（日常使用）       │
                    │  检测 router-*.md 已存在               │
                    │  弹出选择界面                          │
                    │  直接启动 router-* 子智能体             │
                    └──────────────────────────────────────┘
```

---

## 四、技术架构

### 4.1 插件结构

```
agent-model-router/
├── .zcode-plugin/
│   └── plugin.json              # 插件元信息（版本、技能目录、命令目录）
├── commands/
│   ├── router-setup.md          # /router-setup 斜杠命令
│   └── select-provider.md       # /agent-model-router 斜杠命令
├── skills/
│   └── agent-model-router/
│       ├── SKILL.md             # 技能定义（Agent 执行指令）
│       ├── scripts/
│       │   ├── router.py        # 核心脚本（list/search/setup/create-agent）
│       │   └── rankings.py     # 模型排名参考数据
│       └── references/
│           └── model-rankings.md
├── hooks/
│   ├── hooks.json               # Hook 注册
│   └── check-agent-type.js      # PreToolUse Hook：拦截 Explore 类型
├── marketplace.json             # 市场元信息
├── README.md
└── PRD.md                       # 本文档
```

### 4.2 router.py 命令

| 命令 | 用途 | 触发方式 |
|------|------|----------|
| `list` | 列出所有 provider | `/agent-model-router` 自动调用 |
| `models <provider>` | 列出 provider 的模型 | `/agent-model-router` 自动调用 |
| `search <keyword>` | 搜索模型 | `/agent-model-router` 自动调用 |
| `get <provider> <model>` | 获取模型配置详情 | 内部使用 |
| `format <provider> <model>` | 输出 model_ref 格式 | 内部使用 |
| `setup` | 批量生成 router-*.md | `/router-setup` 调用 |
| `create-agent <provider> <model>` | 为单个模型生成定义 | 手动补充新模型时使用 |

### 4.3 生成的子智能体定义格式

```markdown
---
name: router-deepseek-v4-flash-free
description: "agent-model-router 生成的模型路由子智能体：绑定 121628 / deepseek-v4-flash-free..."
model: custom:121628:deepseek-v4-flash-free
color: purple
---
你是绑定 deepseek-v4-flash-free 模型的执行子智能体。直接完成派发的任务，保持输出简洁、结论附证据。
```

关键约束：
- 文件**第一行必须是 `---`**（HTML 注释会破坏 frontmatter 解析 → `agent_missing_frontmatter` 错误）
- `model` 格式必须为 `custom:<provider_id>:<model_name>`

### 4.4 Hook 保护机制

`check-agent-type.js`（PreToolUse Hook）：

```javascript
// 拦截逻辑：
if (agent_type === "Explore") → 拒绝（exit 2）
//   Explore 是只读内置类型，不支持模型绑定，使用会导致假路由

if (flag_file 存在 && agent_type.startsWith("router-")) → 拒绝（exit 2）
//   flag_file 表示有新定义正在生成，防止竞态
//   注：当前两技能架构下 flag_file 不会被创建，此逻辑为防御性保留
```

### 4.5 数据来源

```
~/.zcode/v2/config.json
    └── provider: {
          "<provider_id>": {
            name: "...",
            apiKey: "...",
            models: {
              "<model_name>": { name, enabled, ... }
            }
          }
        }
```

router.py 读取此配置，筛选 `enabled: true` 的 provider 和模型，直接复用 ZCode 已有的配置，无需额外 API key。

---

## 五、已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 模型格式错误导致路由失败 | slash 格式 / 裸模型名 | 统一使用 `custom:<provider_id>:<model_name>` |
| 新生成的定义当前会话不可用 | ZCode 不热重载子智能体定义 | 两技能架构：setup 预生成 + 新会话使用 |
| 定义文件 `agent_missing_frontmatter` | HTML 注释 `<!-- -->` 在 `---` 之前 | setup 生成时确保第一行为 `---` |
| Agent 跳过 create-agent 直接启动 | Agent 未遵循 SKILL.md 指令 | 改为两技能架构：日常使用无需 create-agent |
| Agent 用旧版定义 fallback | 找不到新类型时复用旧类型 | SKILL.md 明确禁止 fallback |
| select-provider.md 与 SKILL.md 矛盾 | 一处仍写 general-purpose | 统一改为 router-* 类型 |

---

## 六、用户操作流程

### 首次使用

1. 安装插件
2. 执行 `/router-setup`
3. 新建会话

### 日常使用

1. 执行 `/agent-model-router` + 任务描述
2. 在弹出界面中为每个 Agent 选择 provider/模型
3. 确认后 Agent 并行启动

### 新增 provider/模型后

1. 重新执行 `/router-setup`
2. 新建会话

---

## 七、设计原则

1. **零配置**：读取 ZCode 已有配置，无需额外设置
2. **真实路由**：通过子智能体定义的 model 字段在运行时切换，非提示词安慰
3. **不依赖 Agent 自觉**：斜杠命令强制加载技能，两技能架构不依赖 Agent 遵循指令
4. **防御性 Hook**：拦截 Explore 类型，防止假路由绕过
5. **最小侵入**：不修改 ZCode 本身，仅利用公开的子智能体机制
