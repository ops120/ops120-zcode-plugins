# agent-model-router

> 一个 ZCode 插件，让你在启动多个 AI Agent 时，为每个 Agent 选择不同的模型和 provider。简单任务用小模型省钱，复杂任务用大模型出力。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-green.svg)](marketplace.json)
[![ZCode Compatible](https://img.shields.io/badge/ZCode-Compatible-purple.svg)](https://github.com/ops120/ops120-zcode-plugins)

---

## 这个插件解决什么问题？

当你在 ZCode 中启动多个 Agent（例如并行分析、多维度评估）时，默认情况下所有 Agent 使用同一个模型。这个插件改变了这一点：

- **成本优化**：简单任务分配给便宜的小模型，复杂任务交给强大的大模型
- **各取所长**：代码生成用擅长代码的模型，文档撰写用擅长写作的模型
- **灵活切换**：自动读取你已有的 ZCode provider 配置，无需额外设置

## 交互流程示例

当你对 ZCode 说 "启动 3 个并行 Agent 分别分析代码、文档和架构" 时：

```
你:  启动 3 个并行 Agent，分别从代码质量、文档完整性、架构合理性三个维度分析项目

ZCode:  (弹出选择界面) 请为每个 Agent 选择 provider 和模型:
        +------------------+-------------------+
        | Agent            | 可选模型          |
        +------------------+-------------------+
        | 代码质量分析     | claude / gemini   |
        | 文档完整性分析   | gpt4 / deepseek   |
        | 架构合理性分析   | claude / qwen     |
        +------------------+-------------------+

你:   选择好每个 Agent 的模型后，ZCode 用不同模型并行启动
```

## 快速开始

### 前置条件

- ZCode 已安装并正常运行
- ZCode 中至少配置了一个 provider（如 OpenAI、Anthropic、Google 等）

### 安装（推荐：Git 仓库方式）

1. 打开 ZCode，点击 **创建 > 添加插件市场**

   ![添加插件市场](demo/添加插件1.png)

2. 选择 **Git 仓库**，粘贴地址：
   ```
   https://github.com/ops120/ops120-zcode-plugins.git
   ```

   ![输入仓库地址](demo/添加插件2.png)

3. 在 **个人** 分类中找到 `agent-model-router`，点击 **安装**

   ![安装插件](demo/添加插件3.png)

4. 重启 ZCode

### 安装（备选：本地方式）

```bash
git clone https://github.com/ops120/ops120-zcode-plugins.git
```

然后在 ZCode 中点击 **创建 > 添加插件市场 > 本地目录**，指向克隆的仓库，在 **个人** 分类中安装。

## 使用方式

### 斜杠命令（最推荐）

在输入框中输入 `/agent-model-router` + 任务描述，**强制触发**插件流程：

```
/agent-model-router 启动多个 agent 来分析这个仓库
```

这是最可靠的方式，不依赖模型"自觉"选技能，harness 会强制加载技能并执行。

### 完整交互示例

```
你:  /agent-model-router 启动多个 agent 来分析这个仓库

ZCode:  (自动运行 router.py list，获取可用 provider)
        (弹出选择界面) 请为每个 Agent 选择 provider 和模型:

        Agent 1 - 代码质量分析:
          ○ OpenAI / gpt-4o
          ● Anthropic / claude-sonnet-4-20250514  (你选了这个)
          ○ DeepSeek / deepseek-chat

        Agent 2 - 文档完整性分析:
          ● OpenAI / gpt-4o  (你选了这个)
          ○ Anthropic / claude-sonnet-4-20250514
          ○ Google / gemini-2.5-flash

        Agent 3 - 架构合理性分析:
          ○ OpenAI / gpt-4o
          ○ Anthropic / claude-sonnet-4-20250514
          ● DeepSeek / deepseek-reasoner  (你选了这个)

你:   (选择完毕，确认)

ZCode:  (并行启动 3 个 Agent，分别使用你选定的模型)
        Agent 1 → Anthropic claude-sonnet-4-20250514  开始分析代码质量...
        Agent 2 → OpenAI gpt-4o                     开始分析文档完整性...
        Agent 3 → DeepSeek deepseek-reasoner         开始分析架构合理性...

        (3 个 Agent 同时运行，各自返回结果)
```

### 为什么不直接说"启动多个 agent"？

插件也支持自然语言触发（如"启动多个并行 Agent"），但斜杠命令更可靠：

| 方式 | 是否保证触发 | 原因 |
|------|-------------|------|
| `/agent-model-router` | ✅ 是 | harness 强制加载技能，不依赖模型 |
| "启动多个 agent" | ❌ 不一定 | 模型可能跳过技能，自己直接操作 |

### 其他用法

```
# 列出所有可用的 provider
/agent-model-router 列出可用的 provider

# 搜索特定模型
/agent-model-router 搜索 gemini 相关的模型

# 查看某个 provider 的所有模型
/agent-model-router 查看 OpenAI 有哪些模型
```

### 命令行方式（进阶）

如果你偏好命令行，可以在技能目录下运行 Python 脚本：

```bash
# 列出所有 provider
python scripts/router.py list

# 搜索模型
python scripts/router.py search gemini

# 列出某个 provider 的模型
python scripts/router.py models openai

# 获取指定模型的路由配置
python scripts/router.py get openai gpt-4o
```

## 工作原理

```
用户请求
    |
    v
[Agent Model Router 插件]
    |
    v
读取 ZCode 配置 (~/.zcode/v2/config.json)
    |
    v
筛选已启用的 provider
    |
    v
弹出交互式选择界面 (AskUserQuestion)
    |
    v
将每个 Agent 路由到用户选择的 provider/模型
```

本插件直接读取 ZCode 已有的配置文件 `~/.zcode/v2/config.json`，无需额外的 API key 或配置文件。

## 更新插件

ZCode 会缓存市场清单，更新插件需要先刷新市场缓存，再检查更新：

### 步骤一：刷新市场缓存

打开 ZCode → 插件市场 → 点击右上角 **齿轮图标** → 选择 **刷新该市场**

![刷新市场缓存](demo/插件更新1.png)

### 步骤二：检查更新

在 **管理已安装** 页面，点击右上角 **检查更新**

![检查更新](demo/插件更新2.png)

### 步骤三：安装新版本

检测到新版本后，点击插件条目进行更新

![安装新版本](demo/插件更新3.png)

> ⚠️ **重要**：如果跳过"刷新市场缓存"直接检查更新，ZCode 会使用旧的缓存数据，导致检测不到新版本。

## 常见问题

**Q: 安装后没有反应？**
A: 确保已重启 ZCode。插件安装后需要重启才能生效。

**Q: 更新版本后还是旧版？**
A: ZCode 不会自动覆盖已安装的插件。请先卸载旧版本，再重新安装。详见上方[更新插件](#更新插件)章节。

**Q: 如何确认当前安装的版本？**
A: 在 ZCode 插件市场中点击插件卡片，查看"版本"字段。安装路径在 `高级信息` 中显示。

**Q: 提示找不到 provider？**
A: 请先在 ZCode 设置中配置至少一个 provider（如 OpenAI API key）。本插件读取的是 ZCode 已有的配置，不会自行创建 provider。

**Q: 我可以同时安装多个插件吗？**
A: 可以。本仓库是一个插件市场，后续会添加更多插件。每个插件独立安装，互不影响。

---

## 完全卸载

ZCode 的插件市场数据分散在三个位置，只清其中一个不够，需要全部清除：

### 清除三个位置

**1. 已安装插件缓存**

```
~/.zcode/cli/plugins/cache/ops120-zcode-plugins/
```

删除整个目录。

**2. 市场数据缓存**

```
~/.zcode/cli/plugins/marketplaces/ops120-zcode-plugins/
```

删除整个目录。

**3. 市场注册表**

```
~/.zcode/cli/plugins/known_marketplaces.json
```

编辑此文件，从 `marketplaces` 数组中移除 `id` 为 `"ops120-zcode-plugins"` 的条目。

### 一行命令（Windows PowerShell）

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.zcode\cli\plugins\cache\ops120-zcode-plugins"
Remove-Item -Recurse -Force "$env:USERPROFILE\.zcode\cli\plugins\marketplaces\ops120-zcode-plugins"
$json = Get-Content "$env:USERPROFILE\.zcode\cli\plugins\known_marketplaces.json" -Raw | ConvertFrom-Json
$json.marketplaces = $json.marketplaces | Where-Object { $_.id -ne "ops120-zcode-plugins" }
$json | ConvertTo-Json -Depth 10 | Set-Content "$env:USERPROFILE\.zcode\cli\plugins\known_marketplaces.json"
```

### 为什么不能只清缓存？

| 文件 | 作用 | 不清的后果 |
|------|------|-----------|
| `cache/ops120-zcode-plugins/` | 已安装插件的代码 | 插件文件还在，功能残留 |
| `marketplaces/ops120-zcode-plugins/` | 市场的插件列表（marketplace.json） | 插件市场里还能看到 |
| `known_marketplaces.json` | 市场注册表 | 市场本身还显示在列表里 |

三处是独立存储的，清了第一处只是"没安装"，但市场还在列表里、插件描述还能看到。必须三处全清才能彻底移除。

---

## 贡献指南：开发新插件

如果你想基于本仓库开发新插件：

### 目录结构

```
ops120-zcode-plugins/
├── marketplace.json              # 插件市场配置
├── agent-model-router/           # 本插件
│   ├── .zcode-plugin/
│   │   └── plugin.json
│   └── skills/
│       └── agent-model-router/
│           ├── SKILL.md
│           └── scripts/
│               └── router.py
└── your-new-plugin/              # 新插件
    ├── .zcode-plugin/
    │   └── plugin.json
    └── skills/
        └── your-skill/
            └── SKILL.md
```

### 步骤

1. 在仓库根目录创建插件目录
2. 在 `marketplace.json` 的 `plugins` 数组中注册：
   ```json
   { "name": "your-new-plugin", "source": "./your-new-plugin" }
   ```
3. 创建 `plugin.json`：
   ```json
   {
     "name": "your-new-plugin",
     "version": "0.1.0",
     "description": "插件描述",
     "author": { "name": "your-name" },
     "skills": "skills"
   }
   ```
4. 创建 `SKILL.md`：
   ```markdown
   ---
   name: your-skill
   description: 什么时候使用这个技能
   ---
   技能内容
   ```
5. 提交并推送：
   ```bash
   git add .
   git commit -m "feat: 新增 your-new-plugin"
   git push
   ```

用户刷新插件市场即可获取新版本。

## 社区

本项目在 [LINUX DO 社区](https://linux.do) 进行开源推广，感谢社区佬友的交流、反馈与建议。

## 作者

你们喜爱的老王 — [B 站 @你们喜爱的老王](https://space.bilibili.com) · [GitHub @ops120](https://github.com/ops120)

## License

MIT
