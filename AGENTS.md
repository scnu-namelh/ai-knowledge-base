# AI 知识库助手 · AGENTS 规范

## 项目概述

AI 知识库助手是一个自动化的技术信息采集与分析系统，定期从 GitHub Trending 和 Hacker News 等平台抓取 AI/LLM/Agent 领域的技术动态，通过 AI 模型进行智能分析，生成结构化知识条目，并支持多渠道（Telegram/飞书）分发，帮助开发者高效追踪技术前沿。

## 技术栈

- **编程语言**: Python 3.12
- **开发框架**: OpenCode + 国产大模型
- **Agent 编排**: LangGraph
- **网页抓取**: OpenClaw
- **代码规范**: PEP 8、snake_case、Google 风格 docstring、禁止裸 print()

## 编码规范

1. **代码风格**: 严格遵循 PEP 8 规范
2. **命名约定**: 所有变量、函数、文件名使用 snake_case 命名
3. **文档注释**: 所有公开函数和类使用 Google 风格 docstring
4. **输出方式**: 禁止使用裸 print()，统一使用 logging 模块进行日志输出
5. **类型提示**: 函数参数和返回值必须添加类型提示

## 项目结构

```
ai-knowledge-base/
├── .opencode/
│   ├── agents/          # Agent 实现
│   └── skills/          # 技能模块
├── knowledge/
│   ├── raw/             # 原始采集数据
│   └── articles/        # 结构化知识条目
└── AGENTS.md
```

## 知识条目 JSON 格式

```json
{
  "id": "string",
  "title": "string",
  "source_url": "string",
  "source_platform": "github|hackernews",
  "summary": "string",
  "tags": ["string"],
  "status": "pending|analyzed|published",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "analysis": {
    "description": "string",
    "tech_category": "string",
    "innovation": "string",
    "difficulty": "string",
    "use_cases": ["string"]
  }
}
```

## Agent 角色概览

| 角色 | 职责 | 主要技能 |
|------|------|----------|
| **采集 Agent** | 从 GitHub Trending 和 Hacker News 抓取 AI/LLM/Agent 相关内容，保存原始数据 | OpenClaw 网页抓取、API 调用、数据清洗 |
| **分析 Agent** | 对原始数据进行 AI 分析，生成结构化知识条目 | LLM 调用、内容分析、知识提取、JSON 格式化 |
| **整理 Agent** | 管理知识条目状态，支持多渠道分发 | 数据存储、状态更新、Telegram 机器人、飞书机器人 |

## 红线（绝对禁止的操作）

1. **禁止提交敏感信息**: 绝不在代码仓库中提交 API Key、令牌、密码等敏感信息
2. **禁止滥用平台 API**: 严格遵守 GitHub 和 Hacker News 的 API 调用频率限制
3. **禁止修改用户数据**: 不收集、不存储、不修改任何用户个人信息
4. **禁止绕过编码规范**: 必须严格遵循本文件规定的编码规范
5. **禁止裸 print()**: 所有输出必须通过 logging 模块
6. **禁止跳过验证**: 代码合并前必须确保没有语法错误和类型错误
