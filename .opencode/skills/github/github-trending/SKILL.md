---
name: github-trending
description: |-
  热点 — 采集/查看/更新/推荐 GitHub Trending 项目数据。触发场景：采集 GitHub 热门、查看 Trending、更新热门数据、推荐开源项目、抓取趋势、爬取热点、刷新采集、浏览榜单。
allowed-tools: WebFetch, Read, Grep, Glob
---

# 热点 — GitHub Trending 采集

## 执行步骤

1. **搜索热点仓库** — 用 WebFetch 访问 `https://github.com/trending`，获取当日热门仓库列表
   - 完成标志：页面已完全加载，所有仓库条目已定位

2. **提取信息** — 从每条结果中提取仓库名、完整 URL、Stars 数、主要语言、Topics、描述
   - 完成标志：每个仓库均已提取完整的 6 字段

3. **过滤** — 只保留与 AI/LLM/Agent 直接相关的项目；只排除标题或描述含「Awesome」的列表类项目
   - 完成标志：已移除所有非相关和列表类项目

4. **去重** — 用 Read 读取 `knowledge/raw/` 下所有历史 JSON 文件，按 `name` 字段逐项比对，排除已采集过的仓库
   - 完成标志：每个候选已与所有历史数据比对

5. **撰写摘要** — 按「项目名 + 做什么 + 为什么值得关注」公式为每个项目写中文摘要
   - 完成标志：每个项目都有一条符合公式的中文摘要

6. **排序取前** — 按 stars 降序排序，截取 Top 15
   - 完成标志：已排序且精确含 15 个项目

7. **输出** — 按以下 JSON 格式返回结果，用 `collected_at` 记录 ISO 8601 时间戳
   - 完成标志：输出已格式化并通过 JSON schema 校验

## 输出格式

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-07-12T00:00:00Z",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "项目名 + 核心功能 + 关注理由",
      "stars": 12345,
      "language": "Python",
      "topics": ["ai", "llm", "agent"]
    }
  ]
}
```

- `items` 上限 15 条，按 stars 降序
- `summary` 中文，格式严格为「项目名 + 做什么 + 为什么值得关注」
- `topics` 至少包含主要技术领域标签
