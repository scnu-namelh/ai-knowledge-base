---
name: tech-summary
description: 当需要对采集的技术内容进行深度分析总结时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# 技术内容深度分析技能

## 使用场景

当需要对从 GitHub Trending、Hacker News 等平台采集的技术内容进行深度分析总结时使用此技能。适用于：
- 技术趋势分析
- 项目价值评估
- 知识库构建

## 执行步骤

1. **读取原始数据**：读取 knowledge/raw/ 目录下最新的采集文件
2. **逐条深度分析**：对每个项目进行分析，包括：
   - 精炼摘要（≤50字）
   - 技术亮点（2-3个，用事实说话）
   - 价值评分（1-10分，附理由）
   - 标签建议
3. **趋势发现**：分析所有项目，提炼共同主题和新概念
4. **输出分析结果**：将分析结果保存为 JSON 格式

## 评分标准

- **9-10分**：改变格局，对整个技术领域有颠覆性影响
- **7-8分**：直接有帮助，解决了重要问题或提供了实用价值
- **5-6分**：值得了解，有一定参考价值但不是必需
- **1-4分**：可略过，价值有限

## 注意事项

- 摘要必须精炼，控制在 50 字以内
- 技术亮点必须基于事实，避免夸大其词
- 评分必须客观，并附上充分的理由
- 9-10分的项目数量严格控制：15个项目中不超过2个
- 标签建议要准确，便于分类和检索
- 趋势发现要基于实际数据分析，不是主观臆断

## 输出格式

```json
{
  "source": "tech-summary",
  "skill": "tech-summary",
  "analyzed_at": "2026-07-12T00:00:00Z",
  "raw_source": "github-trending-2026-07-12",
  "trends": {
    "common_themes": ["主题1", "主题2"],
    "new_concepts": ["新概念1", "新概念2"]
  },
  "items": [
    {
      "name": "项目名称",
      "url": "https://github.com/owner/repo",
      "concise_summary": "精炼摘要（≤50字）",
      "tech_highlights": ["亮点1", "亮点2"],
      "score": 8,
      "score_reason": "评分理由",
      "suggested_tags": ["tag1", "tag2"],
      "raw_data": {}
    }
  ]
}
```

## 字段说明

- `source`: 固定为 "tech-summary"
- `skill`: 固定为 "tech-summary"
- `analyzed_at`: ISO 8601 格式的分析时间
- `raw_source`: 原始数据文件名
- `trends`: 趋势分析结果
  - `common_themes`: 共同主题数组
  - `new_concepts`: 新概念数组
- `items`: 分析项目数组
  - `name`: 项目名称
  - `url`: 项目 URL
  - `concise_summary`: 精炼摘要（≤50字）
  - `tech_highlights`: 技术亮点数组（2-3个）
  - `score`: 评分（1-10）
  - `score_reason`: 评分理由
  - `suggested_tags`: 标签建议数组
  - `raw_data`: 原始数据对象
