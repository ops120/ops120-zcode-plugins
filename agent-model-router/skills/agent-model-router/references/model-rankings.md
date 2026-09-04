# 模型排行榜参考数据

> 快照日期：2026-09-02；数据来源：Chatbot Arena（Text/Code）、Artificial Analysis、OpenRouter。
> 使用 `rankings` 命令展示，选择模型时作为推荐依据。

## Arena Text 榜（文本对话，Elo，400 模型 / 800 万票）

| 排名 | 模型 | 厂商 | Elo |
|------|------|------|-----|
| 1 | claude-fable-5 | Anthropic | 1507 |
| 2 | claude-opus-4-6-high | Anthropic | 1505 |
| 3 | claude-fable-5.1-max | Anthropic | 1504 |
| 4 | claude-opus-4-7-high | Anthropic | 1502 |
| 5 | muse-spark-1.2 (xHigh) | Meta | 1499 |
| 8 | gemini-3.8-flash-high | Google | 1494 |
| 12 | kimi-k3-max | Moonshot | 1489 |
| 17 | gpt-5.6-sol-xhigh | OpenAI | 1483 |
| 20 | glm-5.3-max | 智谱 | 1482 |

## Arena Code 榜（WebDev，1765 封顶）

| 排名 | 模型 | 厂商 | 分数 |
|------|------|------|------|
| 1 | claude-fable-5.1-max | Anthropic | 1765 |
| 2 | qwen3.8-max-0902 | Alibaba | 1688 |
| 3 | claude-opus-5-max | Anthropic | 1687 |
| 4 | kimi-k3-max | Moonshot | 1674 |
| 5 | qwen3.8-max | Alibaba | 1669 |
| 7 | grok-4.6-high | SpaceXAI | 1629 |
| 8 | claude-fable-5 | Anthropic | 1628 |
| 9 | hy4-preview | 腾讯 | 1626 |
| 12 | glm-5.3-max | 智谱 | 1609 |
| 13 | glm-5.3-flash | 智谱 | 1604 |
| 15 | gemini-3.7-flash-high | Google | 1587 |
| 18 | deepseek-v4-flash-high | DeepSeek | 1581 |

## Arena Document 榜（文档处理，32 万票 / 39 模型）

| 排名 | 模型 | 厂商 | Elo |
|------|------|------|-----|
| 1 | claude-opus-5-high | Anthropic | 1520 |
| 2 | claude-opus-4-6 | Anthropic | 1510 |
| 3 | claude-opus-4-6-high | Anthropic | 1506 |
| 4 | claude-fable-5 | Anthropic | 1504 |
| 5 | claude-opus-4-7 | Anthropic | 1498 |
| 7 | gpt-5.5-high | OpenAI | 1485 |
| 8 | claude-sonnet-4-6 | Anthropic | 1483 |
| 15 | gpt-5.4 | OpenAI | 1470 |
| 17 | gemini-3.5-flash-high | Google | 1465 |

## Artificial Analysis 综合智能指数

| 排名 | 模型 | 厂商 | 指数 |
|------|------|------|------|
| 1 | Claude Fable 5.1 (max) | Anthropic | 66 |
| 3 | Claude Opus 5 (max) | Anthropic | 63 |
| 6 | Muse Spark 1.3 (max) | Meta | 62 |
| 9 | GPT-6 Astra (max) | OpenAI | 61 |

## OpenRouter 用量榜（API 采用率）

| 排名 | 模型 | 厂商 | Token 量 |
|------|------|------|---------|
| 1 | GLM 5.3 Flash | 智谱 | 11.9T |
| 2 | GPT-5.6 Luna | OpenAI | 11.6T |
| 3 | DeepSeek V4 Flash 0731 | DeepSeek | 11.3T |
| 4 | Hy4 Preview | 腾讯 | 11T |
| 7 | MiniMax M3 | MiniMax | 5.15T |
| 8 | MiMo-V2.5 | 小米 | 4.5T |
| 10 | Gemini 3.7 Flash | Google | 2.63T |

## 中文榜（SuperCLUE / Arena 国产）

- 通义千问 Qwen3.8-Max：网页开发全球第 2、视觉理解第 3
- 智谱 GLM：Arena 文本对话国产前列
- Kimi K3 (Max)：Agent 能力第 6
- MiniMax H3：图生视频全球第 1
- 字节 Seedream 5.0 / Seedance 2.0：图像视频生成前列

## 能力→模型推荐速查

| 任务 | 首选 | 备选 |
|------|------|------|
| 代码生成 | Claude Fable 5 | Qwen3.8-Max、GPT-6 Astra |
| 写作/文档 | Claude Fable 5 | Gemini 3.8 Flash |
| 复杂推理 | Claude Opus 5 | DeepSeek V4 Flash |
| 快速响应/低成本 | GLM 5.3 Flash | GPT-5.6 Luna |
| Agent/工具调用 | Kimi K3 | Claude Opus 5 |
| 多模态视觉 | Qwen3.8-Max | Gemini 3.8 Flash |
| 数据隐私（本地） | Ollama 本地模型 | - |
