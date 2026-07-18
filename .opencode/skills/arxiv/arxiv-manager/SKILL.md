---
name: arxiv-manager
description: |-
  论文管理 — 去重、排序、格式化和存储 arXiv 论文。触发场景：管理论文、去重检查、排序整理、保存到 paperReview。
allowed-tools: Read, Grep, Glob, Write, Edit
---

# arXiv 论文管理 Skill

## 执行步骤

1. **读取论文数据** — 读取前序环节生成的完整论文信息
   - 完成标志：成功读取论文数据

2. **去重检查** — 检查并移除重复的论文（基于 arXiv ID）
   - 完成标志：重复论文已移除

3. **历史对比** — 用 Read 读取 `paperReview/` 下所有历史 JSON 文件，按 arXiv ID 逐项比对
   - 完成标志：与历史数据对比完成

4. **排序整理** — 按提交日期降序排序论文
   - 完成标志：论文已按日期排序

5. **数量控制** — 确保最终输出 Top 20 篇论文
   - 完成标志：精确保留 20 篇论文

6. **格式化存储** — 将论文数据格式化为标准 JSON 格式并保存到 paperReview/ 目录
   - 完成标志：文件成功保存

7. **输出** — 按以下 JSON 格式返回结果，用 `collected_at` 记录 ISO 8601 时间戳
   - 完成标志：输出已格式化并通过 JSON schema 校验

## 文件命名规范

文件命名格式：`arxiv-{date}.json`

- `{date}`: 采集日期，格式为 YYYYMMDD
- 示例：`arxiv-20260712.json`

## 输出格式

```json
{
  "source": "arxiv-papers",
  "skill": "arxiv-papers",
  "collected_at": "2026-07-12T00:00:00Z",
  "items": [
    {
      "arxiv_id": "2607.08758",
      "title": "论文标题",
      "authors": ["作者1", "作者2"],
      "url": "https://arxiv.org/abs/2607.08758",
      "pdf_url": "https://arxiv.org/pdf/2607.08758",
      "chinese_summary": "中文摘要内容",
      "abstract": "完整英文摘要内容",
      "submitted_date": "2026-07-09",
      "categories": ["cs.AI", "cs.LG"],
      "keywords": ["关键词1", "关键词2"]
    }
  ]
}
```

- `items` 精确 20 条，按提交日期降序
- 保存到 `paperReview/` 目录
