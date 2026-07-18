---
name: arxiv-domain-filter
description: |-
  领域过滤 — 筛选 arXiv 人工智能领域论文。触发场景：过滤论文领域、筛选 AI 论文、分类论文、确认相关性检查。
allowed-tools: Read, Grep, Glob
---

# arXiv 领域过滤 Skill

## 执行步骤

1. **读取论文数据** — 读取前序环节生成的完整论文信息
   - 完成标志：成功读取论文数据

2. **分类验证** — 验证论文的 arXiv 分类是否属于人工智能相关领域
   - 完成标志：所有论文分类已验证

3. **内容相关性检查** — 基于标题和摘要检查论文内容是否与 AI 相关
   - 完成标志：内容相关性检查完成

4. **领域分类** — 为符合要求的论文标记具体的 AI 子领域
   - 完成标志：AI 子领域标记完成

5. **关键词提取** — 为每篇论文提取相关关键词
   - 完成标志：关键词提取完成

6. **质量筛选** — 排除明显不相关或质量过低的论文
   - 完成标志：质量筛选完成

7. **输出** — 按以下 JSON 格式返回结果
   - 完成标志：输出已格式化并通过 JSON schema 校验

## 人工智能领域分类标准

### 核心领域（必须包含）
- cs.AI - Artificial Intelligence（主要）

### 辅助领域（可包含）
- cs.LG - Machine Learning
- cs.CL - Computation and Language
- cs.CV - Computer Vision and Pattern Recognition
- cs.RO - Robotics
- cs.MA - Multiagent Systems
- cs.NE - Neural and Evolutionary Computing

## 输出格式

```json
[
  {
    "arxiv_id": "2607.08758",
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "url": "https://arxiv.org/abs/2607.08758",
    "pdf_url": "https://arxiv.org/pdf/2607.08758",
    "abstract": "完整英文摘要内容",
    "comments": "论文评论（如适用）",
    "submitted_date": "2026-07-09",
    "categories": ["cs.AI", "cs.LG"],
    "is_relevant": true,
    "ai_subdomain": "机器学习",
    "keywords": ["关键词1", "关键词2"],
    "source": "arxiv"
  }
]
```

- is_relevant 标记论文是否属于 AI 领域
- ai_subdomain 标记具体的 AI 子领域
- 保留相关论文，过滤不相关论文
