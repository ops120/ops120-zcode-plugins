---
description: 为所有已启用的 provider/模型批量生成子智能体定义（首次使用前执行）
allowed-tools: Bash, Skill
skills: agent-model-router
---

# router-setup

为所有已启用的 provider/模型批量生成 ZCode 子智能体定义文件（`~/.zcode/agents/router-*.md`）。

## 执行步骤

1. 加载 agent-model-router 技能以获取脚本路径
2. **先告知用户**：「将对每个模型发送真实探测请求，通常需要 1~2 分钟，请耐心等待。」然后再执行批量生成命令：

```bash
python "<技能目录>/scripts/router.py" setup
```

如果用户指定了 `--force` 或要求"重新生成"/"清除旧定义"，加上 `--force` 参数：

```bash
python "<技能目录>/scripts/router.py" setup --force
```

默认会对每个模型发送一次真实探测请求（"今天周几"），只给探测通过的模型生成定义；服务端拒绝的（如 token 失效）自动跳过并注明原因。如果用户要求跳过探测（追求速度），加 `--no-test`：

```bash
python "<技能目录>/scripts/router.py" setup --force --no-test
```

3. 输出结果后告知用户：「定义已生成，请**新建会话**后使用 `/agent-model-router` 启动多模型 Agent。」

## 注意

- 执行一次即可，后续不需要重复（除非新增了 provider 或模型）
- 定义文件在新建会话时才会被 ZCode 加载
- 文件名格式：`router-<模型名>.md`，已存在的同名文件会被覆盖
