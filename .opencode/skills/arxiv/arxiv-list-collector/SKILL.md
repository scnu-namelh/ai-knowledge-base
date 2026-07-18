---
name: arxiv-list-collector
description: |-
  论文列表 — 从 arXiv 获取最新人工智能领域论文列表。触发场景：获取 arXiv 最新论文、查看 cs.AI 论文、收集 arXiv 列表、获取论文元数据。
allowed-tools: WebFetch, Read, Grep, Glob
---

# arXiv 列表采集 Skill

## 执行步骤

1. **访问列表页面** — 用 WebFetch 访问 `https://arxiv.org/list/cs.AI/recent`，获取最新人工智能领域论文列表
   - 完成标志：页面已完全加载，所有论文条目已定位

2. **提取基本信息** — 从每条结果中提取 arXiv ID、标题、作者、提交日期、分类标签
   - 完成标志：每篇论文均已提取完整信息

3. **构建链接** — 为每篇论文构建详情页链接和 PDF 下载链接
   - 完成标志：URL 和 PDF 链接正确构建

4. **初步过滤** — 排除明显不属于人工智能领域的论文，优先保留 cs.AI 分类
   - 完成标志：已移除明显不相关的论文

5. **批量收集** — 收集 Top 20 篇最新论文
   - 完成标志：已收集完整的 20 篇论文

6. **输出** — 按以下 JSON 格式返回结果
   - 完成标志：输出已格式化并通过 JSON schema 校验

## 输出格式

```json
[
  {
    "arxiv_id": "2607.08758",
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "url": "https://arxiv.org/abs/2607.08758",
    "pdf_url": "https://arxiv.org/pdf/2607.08758",
    "submitted_date": "2026-07-09",
    "categories": ["cs.AI", "cs.LG"],
    "source": "arxiv"
  }
]
```

- 收集 20 篇最新论文
- 主要分类为 cs.AI，可辅助包含 cs.LG、cs.CL、cs.CV、cs.RO、cs.MA
- 提交日期格式为 YYYY-MM-DD
