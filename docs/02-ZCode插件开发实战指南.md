# ZCode 插件开发实战指南（速查手册）

> 基于一次完整的 ZCode 插件（agent-model-router）开发、发布、安装、排错全过程整理，所有坑都是真实踩过的。配合[官方文档](https://zcode.z.ai/cn/docs/plugin)食用。
>
> **这篇适合谁**：已经在写或准备调试 ZCode 插件的开发者，按症状来查问题、查路径、查字段。
> 第一次上手做插件 → 先跟[《从零发布你的第一个 ZCode 插件》](01-从零发布你的第一个ZCode插件.md)走一遍；
> 想理解坑背后的原理、做更可靠的插件 → 看[《Agent 插件开发通用方法论》](03-Agent插件开发通用方法论.md)。

---

## 〇、症状速查表（先查这里）

| 症状 | 大概率原因 | 修复动作 | 详见 |
|------|-----------|---------|------|
| 安装后 skill 不触发 | ① 插件没加载成功 ② 触发匹配问题 | 先去 设置 → 技能 → Plugin 技能 分组看列表：没有 → 解决加载；有 → 换说法或 `/` 手动触发 | 二、六 |
| `Skill not found: xxx` | skill 根本没注册到 ZCode，不是触发词问题 | 按 6.4 排查链路检查，修好后**停用再启用插件**强制重载 | 六 |
| 推了新版，检查更新却说"已是最新" | 没刷新市场缓存 | 先刷新该市场，再检查更新（两步缺一不可） | 四 |
| 改了 version 还是不提示更新 | marketplace.json 和 plugin.json **两处 version 只改了一处** | 两处同步改 | 三、四 |
| 添加市场报 `Marketplace manifest not found` | marketplace.json 不在仓库根目录 | 市场清单在根目录，插件放二级子目录 | 三 |
| `Agent type not found` | 调用了本会话刚生成的子智能体定义，未加载 | 新建会话；插件侧可加标志文件 + 双 Hook 防护 | 六；方法论 2.3 |
| 子智能体定义报 `agent_missing_frontmatter` | 文件第一行不是 `---`（前面混入了注释/横幅/BOM） | 生成器去掉一切前置内容，`head -1` 检查 | 一；方法论 1.4 |
| 子智能体运行在错误的模型上（不报错） | 定义文件 `model` 字段格式不对（裸名/slash 格式），**静默错误** | 换平台原生格式，用探测链锁定 | 方法论 1.2 |
| `Turn execution failed` | 只是包装，真实原因在 cause 链（多为 provider 业务错误） | 平台日志 grep error 看底层错误码 | 六 |
| 卸载后设置里还有残留 | 插件数据分散在 5 处独立存储 | 按清单全清（含注册表 JSON、生成的定义文件） | 六；根 README「[完全卸载](../README.md#完全卸载)」 |
| 手改配置文件后插件"消失"或注册表混乱 | 运行时手改 `installed_plugins.json`，进程内存还是旧数据 | 插件注册一律走 ZCode 界面，文件只读不改 | 六 |
| 本地改了 cache 但过会儿又变回去 | 市场源刷新时回写覆盖 cache | 改源头仓库并 push，不要打本地补丁 | 四；[方法论 5.3](03-Agent插件开发通用方法论.md) |
| 同一插件出现两个市场来源的记录 | config.json 的 enabledPlugins 有孤儿条目 | 界面卸载旧来源；不行再清 config.json 多余条目后重启 | 七 |

---

## 一、插件基础

### 1.1 插件是什么

插件就是一个**文件夹**：根目录放一份清单 `plugin.json`（唯一必需），再按需放各类组件目录（全部可选）。

```
my-plugin/
├── .zcode-plugin/
│   └── plugin.json    # 清单（唯一必需）
├── commands/          # 斜杠命令，每个一个 .md
├── skills/            # 技能，每个子目录含 SKILL.md
├── agents/            # 子智能体 .md
├── hooks/hooks.json   # 钩子
└── .mcp.json          # MCP 服务声明
```

> 清单位置按优先级查找：`.zcode-plugin/plugin.json`（推荐）→ `.claude-plugin/plugin.json`（兼容 Claude Code）。

### 1.2 plugin.json 字段速查

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "一句话描述",
  "author": { "name": "your-name" },
  "license": "MIT",
  "skills": "skills",
  "commands": "commands"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 须匹配 `^[a-z0-9][a-z0-9._-]{0,127}$`（小写字母/数字开头） |
| `version` | | 缺省 0.0.0，**每次发版必须改**（且与 marketplace.json 同步，见第三章） |
| `description` | | 显示在插件管理界面 |
| `skills` / `commands` | | 目录字符串、路径数组或内联对象 |
| `userConfig` | | 用户可在插件详情页"配置区"填写的参数项（含敏感值打码机制） |

> 全字段（含 hooks、mcpServers、agents、dependencies 等）见[官方文档](https://zcode.z.ai/cn/docs/plugin)。

### 1.3 SKILL.md 格式

技能文件位于 `skills/<技能名>/SKILL.md`，frontmatter 支持以下字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 技能名，缺省取所在目录名 |
| `description` | ✅ | **触发说明，最长 1024 字符，越准越易被自动调用** |
| `when_to_use` | | 补充触发时机描述 |

```markdown
---
name: my-skill
description: 什么时候使用这个技能，写清楚触发场景和关键词
when_to_use: 补充触发时机
---

技能正文（AI 加载后按此执行）
```

> ⚠️ frontmatter 必须从文件**第一行**开始，之前哪怕一个 HTML 注释都会导致整体解析失败，且报错不指明真实原因。

### 1.4 命令 .md 格式

命令位于 `commands/<命令名>.md`，命令名取自文件名（须匹配 `^[a-z0-9][a-z0-9_:-]{0,63}$`）：

```markdown
---
description: 命令描述（必填）
argument-hint: "[参数提示]"
---

命令正文，$ARGUMENTS 代表用户传入的全部参数，$1 / $2 代表位置参数
```

frontmatter 还支持 `allowed-tools`（限制可用工具）、`skills`（自动挂载技能）、`model`（覆盖模型）等字段。

### 1.5 Skill 与 Command 的区别（重要）

| | Skill | Command |
|---|-------|---------|
| 触发方式 | AI 根据 description **自动匹配**，可能被忽略 | 用户输入 `/` **显式调用**，必然执行 |
| 可靠性 | 不保证触发 | 100% 触发 |
| 适用场景 | 辅助性、上下文增强 | 强制流程、固定操作 |

**结论：需要"必须执行"的流程，用 Command 而不是 Skill。** Skill 的自动触发本质上是一个概率事件——AI 读了 description 后仍可能决定不调用它，这是大模型的行为特性，不是配置问题。

---

## 二、Skill 触发机制

### 2.1 自动触发的真相

官方文档说"技能合适时机会自动触发；描述越准越易被自动调用"。**但实测结论是：自动触发不保证。**

我们把同一个 skill 的 description 改了四五轮（加触发词、按优先级排列、加"必须触发"标记、写禁止事项），AI 照样在用户说"启动多个 agent"时无视 skill 直接干活。**description 写得再好，也只是提高概率，不是开关。**

### 2.2 提高 description 触发率的经验

仍然值得做，能显著提高命中率：

- **开头直接写使用场景**："当用户要启动多个 agent、多维度分析时必须使用"
- **列举用户真实的说法**作为触发词："启动多个 agent、安排多个专家、多维度、并行分析"
- **控制在合理长度**：太长 AI 反而抓不住重点
- `when_to_use` 补充触发时机，与 description 呼应

### 2.3 手动触发（100% 可靠）

用户在输入框输入 `/`，从「技能」分组手动选用。所有已注册的 skill 都会出现在列表里。

### 2.4 需要强制执行的流程 → 用 Command

Command（斜杠命令）是用户显式调用的，不存在"AI 忘了触发"的问题。如果你的功能必须执行（比如"启动 Agent 前必须选模型"），提供 `/xxx` 命令，并在文档里教用户用它。

---

## 三、发布到 GitHub

### 3.1 仓库结构（插件市场模式）

一个仓库 = 一个插件市场，可以放多个插件：

```
ops120-zcode-plugins/           # 仓库根目录
├── marketplace.json            # ⚠️ 必须在根目录
├── README.md
└── agent-model-router/         # 插件放二级子目录
    ├── .zcode-plugin/
    │   └── plugin.json
    ├── commands/
    │   └── select-provider.md
    └── skills/
        └── agent-model-router/
            ├── SKILL.md
            └── scripts/
```

### 3.2 marketplace.json

```json
{
  "name": "my-market",
  "description": "市场描述",
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./my-plugin",
      "description": "插件描述",
      "version": "0.1.0"
    }
  ]
}
```

**踩坑记录**：把 marketplace.json 放进插件子目录、或把插件直接放在仓库根目录，都会报错：

```
Marketplace manifest not found in directory: xxx
```

正确姿势：**marketplace.json 在仓库根目录，插件在二级子目录**，`source` 用相对路径 `./插件名` 指向。

### 3.3 版本号必须双同步（血的教训）

发版时**两处 version 都要改**：

1. `marketplace.json` 里该插件条目的 `version`
2. 插件自身的 `.zcode-plugin/plugin.json` 的 `version`

官方文档原文：

> 「最新版本」取自市场 marketplace.json 里该插件条目声明的 version，「已安装版本」取自插件自身的 plugin.json。**如果市场条目发版时忘了更新 version，即使插件代码已更新也不会提示可更新**。

只改 plugin.json 不改 marketplace.json → 用户永远收不到更新提示。

---

## 四、安装与更新（踩坑重灾区）

### 4.1 安装

1. 打开 ZCode → **设置 → 插件**
2. 点右上角 **创建 → 添加插件市场**
3. 填 GitHub 仓库地址（如 `https://github.com/user/repo.git`）
4. 在 **个人** 分段找到插件 → 点 **安装**
5. 新装插件默认启用，组件立即可用

### 4.2 核心事实：ZCode 不会自动更新插件

**已安装的插件不会跟随 GitHub 仓库自动更新。** 就算你推了新版本，用户本地还是旧版，必须手动触发更新。

### 4.3 正确的更新流程（三步，一步都不能少）

1. **刷新市场缓存**：插件市场页 → 点搜索框上方的 **齿轮图标** → 找到对应市场 → **刷新该市场**
2. **检查更新**：管理已安装页面 → 点 **检查更新**
3. **安装新版本**

> ⚠️ 跳过第 1 步直接检查更新，ZCode 用的是本地缓存的市场清单（旧 version），永远提示"已是最新"。

### 4.4 ZCode 的两个缓存位置

| 位置 | 内容 | 对应操作 |
|------|------|---------|
| `~/.zcode/cli/plugins/marketplaces/` | 市场清单缓存（marketplace.json 快照） | 「刷新该市场」更新它 |
| `~/.zcode/cli/plugins/cache/` | 已安装插件文件（按版本号目录存放） | 「安装/更新」写入它 |

版本判断链路：**GitHub 上的 marketplace.json → 刷新 → 本地 marketplaces/ 缓存 → 检查更新对比版本 → 下载到 cache/新版本目录**。

### 4.5 界面操作无效时的手动清理

```bash
# 1. 清市场清单缓存
rm -rf ~/.zcode/cli/plugins/marketplaces/<市场名>

# 2. 清插件安装缓存
rm -rf ~/.zcode/cli/plugins/cache/<市场名>

# 3. 重启 ZCode，重新走安装流程
```

**踩坑记录**：只清 cache 不清 marketplaces，重新安装时 ZCode 可能仍从旧的市场清单读版本号，装回来还是旧版。

---

## 五、Hook 强制拦截

插件支持 `hooks/hooks.json`（标准位置自动发现），当前支持 7 个事件：

```
SessionStart、UserPromptSubmit、PreToolUse、PermissionRequest、
PostToolUse、PostToolUseFailure、Stop
```

其中 `PreToolUse` 事件可以在工具调用前拦截（exit 2 拒绝该次调用），是绕过"skill 不可靠"的根本方案：在 AI 启动 Agent 前强制校验，不满足条件直接拒绝并提示正确做法。实现复杂度高，适合对强制性要求极高的场景。

本仓库的 agent-model-router 就用了双 Hook（PreToolUse 拦截不安全派发 + SessionStart 清除标志文件），具体模式见[《通用方法论》的"防护闭环"章节](03-Agent插件开发通用方法论.md)。

---

## 六、调试与排查

### 6.1 日志位置

| 日志 | 路径 | 内容 |
|------|------|------|
| CLI 日志 | `~/.zcode/cli/log/zcode-YYYY-MM-DD.jsonl` | 工具调用、插件解析、skill 加载错误 |
| 桌面端日志 | `~/.zcode/v2/logs/YYYY-MM-DD.log` | 主进程、RPC 调用、MCP 连接 |

### 6.2 第一件事：确认插件被加载

在 CLI 日志里搜 `bootstrap.app.startup.plugins.completed`：

```json
{
  "event": "bootstrap.app.startup.plugins.completed",
  "context": {
    "enabledPluginCount": 6,   // 启用的插件数
    "pluginCount": 9,          // 已安装的插件数
    "skillRootCount": 6,       // 加载的 skill 根目录数
    "hookCount": 0
  }
}
```

- `pluginCount` 变了但 `enabledPluginCount` 没变 → 插件装了但没启用
- `skillRootCount` 没变 → skill 没被加载

### 6.3 "Skill not found" 意味着什么

日志里出现：

```
"toolName":"Skill","error":{"message":"Skill not found: agent-model-router"}
```

表示 **skill 根本没注册到 ZCode**，不是触发词的问题。此时改 description 毫无意义，先解决加载问题。

### 6.4 排查链路（按顺序检查）

```
1. ~/.zcode/cli/plugins/installed_plugins.json
   → 插件在不在 plugins[] 数组里？version 对不对？

2. ~/.zcode/cli/config.json
   → enabledPlugins 里有没有 "插件名@市场名": true？

3. ~/.zcode/cli/plugins/cache/<市场>/<插件>/<版本>/
   → 文件在不在？SKILL.md 存不存在？

4. ~/.zcode/cli/plugins/marketplaces/<市场>/
   → 市场清单缓存是不是旧的？
```

### 6.5 关键机制：skill 注册表缓存在进程内存

**ZCode 运行期间手改配置文件，进程不一定重新读取。** 我们实测：手动修好 `installed_plugins.json` 后调用 skill 依然报 "Skill not found"，因为进程内存里还是启动时缓存的旧数据。

正确做法（官方文档确认的热加载机制）：

> 启用或停用插件后，ZCode 会自动刷新受影响的技能和会话，让改动生效。

所以改完任何插件相关文件后，去 **设置 → 插件 → 该插件 → 停用 → 启用**，强制 ZCode 重新加载。

### 6.6 血泪教训：不要运行时手改 installed_plugins.json

我们排查时清空过 `installed_plugins.json` 的 `plugins[]` 数组，结果：

- ZCode 里插件"消失"
- 重新安装时注册表混乱（config.json 里残留 `插件名@旧市场名: true` 的孤儿条目）
- 出现同一插件两个 marketplace 来源的冲突记录

**结论：插件注册相关文件全部走 ZCode 界面操作，文件只读不改。**

### 6.7 子智能体/模型类插件追加排查（选读）

如果你的插件像 agent-model-router 一样会生成子智能体定义文件（`~/.zcode/agents/*.md`）或调用模型 API：

- **定义文件只在会话启动时加载**：运行时新生成的定义在本会话不可用，且无 API 可强制重载 → 提示用户新建会话，或用 Hook 拦截误用
- **子智能体执行失败的排查**：`~/.zcode/cli/agents/sess_<id>/agent_xxx/` 下有 `metadata.json`（绑定的 model、status、error、耗时）和 `task.output`（输出/报错）；再到 CLI 日志 grep `"level":"error"` 看 cause 链里的真实错误——`Turn execution failed` 只是包装
- 拿到底层错误码才算找到根因，"可能大概是"不算诊断

---

## 七、常见问题 FAQ

**Q: 安装后 skill 不触发？**
A: 分两步判断：
1. 去 **设置 → 技能 → Plugin 技能** 分组看列表里有没有这个 skill
2. **有** → 是触发匹配问题，换说法或用 `/` 手动触发；**没有** → 插件没加载成功，回插件页确认启用状态，或停用再启用

**Q: 推了新版本，检查更新却说已是最新？**
A: 没刷新市场缓存。先去市场源面板（齿轮图标）**刷新该市场**，再检查更新。ZCode 的版本对比基于本地缓存的市场清单。

**Q: 更新了 version 还是不提示？**
A: 检查 `marketplace.json` 和 `plugin.json` **两处 version 是否都改了**。更新检测对比的是 marketplace.json 条目里的 version，只改 plugin.json 没用。

**Q: Skill not found: xxx？**
A: skill 没注册。按 6.4 的排查链路检查，修复后**停用再启用插件**强制重载（改文件直接生效是错觉，注册表在进程内存里）。

**Q: 插件市场添加失败，报 Marketplace manifest not found？**
A: marketplace.json 必须在仓库（或所选目录）**根目录**。插件放在二级子目录，通过 `plugins[].source` 相对路径引用。

**Q: skill 触发不稳定，时灵时不灵？**
A: 正常现象。自动触发是大模型基于 description 的概率判断。要稳定性：让用户 `/` 手动触发，或改造成 command，或用 PreToolUse hook 强制拦截（见第五章）。

**Q: 同一插件出现两个来源（不同 marketplace）的记录？**
A: config.json 的 `enabledPlugins` 里有孤儿条目（如 `插件名@旧市场名`）。在 ZCode 界面卸载旧来源的插件；实在不行清理 `~/.zcode/cli/config.json` 中多余的条目后**重启**。

---

## 附：本文的完整实例

完整可运行的插件示例：[ops120/ops120-zcode-plugins](https://github.com/ops120/ops120-zcode-plugins)

包含：技能（SKILL.md）+ 命令（commands/）+ Python 脚本（读取 ZCode provider 配置、模型排行榜缓存）+ 双 Hook 的完整组合，可直接 clone 参考目录结构与文件写法。

---

[← 返回开发文档导航](README.md) ｜ 下一篇：[Agent 插件开发通用方法论 →](03-Agent插件开发通用方法论.md)
