---
name: github-trending
description: 当需要采集 GitHub 热门开源项目时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# GitHub Trending 采集技能

## 使用场景

当需要从 GitHub Trending 采集 AI/LLM/Agent 领域的热门开源项目时使用此技能。适用于：
- 每日技术热点采集
- 技术趋势分析
- 开源项目推荐

## 执行步骤

1. **搜索热门仓库**：通过 GitHub API 或网页访问 GitHub Trending，获取当前热门开源仓库列表
2. **提取信息**：从搜索结果中提取仓库名称、URL、Stars 数、语言、Topics 和描述信息
3. **过滤筛选**：纳入 AI/LLM/Agent 相关项目，排除 Awesome 列表类项目
4. **去重处理**：检查已存在的 raw 数据文件，去除重复的仓库
5. **撰写中文摘要**：按照公式「项目名+做什么+为什么值得关注」生成简洁明了的中文摘要
6. **排序取前**：按 Stars 数降序排序，取 Top 15 个项目
7. **输出数据**：将结果输出为 JSON 格式，保存到 knowledge/raw/github-trending-YYYY-MM-DD.json

## 注意事项

- 必须严格筛选 AI/LLM/Agent 相关项目，不采集无关内容
- 排除标题或描述中包含「Awesome」的列表类项目
- 摘要必须使用中文表述，遵循「项目名+做什么+为什么值得关注」的格式
- 检查已存在的 raw 数据文件，避免重复采集
- 按 Stars 数降序排序，确保优先采集最热门项目
- 输出文件必须使用正确的日期格式 YYYY-MM-DD

## 输出格式

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-07-12T00:00:00Z",
  "items": [
    {
      "name": "项目名称",
      "url": "https://github.com/owner/repo",
      "summary": "中文摘要内容",
      "stars": 12345,
      "language": "Python",
      "topics": ["ai", "llm", "agent"]
    }
  ]
}
```

## 字段说明

- `source`: 固定为 "github-trending"
- `skill`: 固定为 "github-trending"
- `collected_at`: ISO 8601 格式的采集时间
- `items`: 项目数组，最多 15 个项目
- `name`: 仓库名称
- `url`: 仓库完整 URL
- `summary`: 中文摘要
- `stars`: Stars 数量
- `language`: 主要编程语言
- `topics`: 仓库标签数组
