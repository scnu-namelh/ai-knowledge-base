---
name: arxiv-papers
description: |-
  论文 — 采集/获取/更新 arXiv 人工智能领域最新论文数据。触发场景：抓取 arXiv 人工智能论文、获取最新 AI 论文、更新人工智能论文库、浏览 AI 研究动态、采集人工智能进展、查看 AI arXiv 趋势、收录前沿 AI 论文。
allowed-tools: WebFetch, Read, Grep, Glob, Write
---

# 论文 — arXiv 人工智能领域论文采集

## 执行步骤

### 方式一：完整流程（推荐）
依次调用以下子技能完成全流程：

1. **arxiv-list-collector** — 获取 arXiv 最新论文列表
2. **arxiv-detail-collector** — 获取论文完整详情和摘要
3. **arxiv-domain-filter** — 筛选人工智能领域论文
4. **arxiv-summary-writer** — 撰写中文摘要
5. **arxiv-manager** — 去重、排序、存储

### 方式二：单步执行
也可以单独执行以下步骤：

1. **访问人工智能论文列表** — 用 WebFetch 访问 `https://arxiv.org/list/cs.AI/recent`，获取最新人工智能领域论文列表
   - 完成标志：页面已完全加载，所有论文条目已定位

2. **提取论文信息** — 从每条结果中提取标题、作者、arXiv ID、论文 URL、PDF URL、摘要、提交日期、主题标签
   - 完成标志：每篇论文均已提取完整的 8 字段

3. **人工智能领域过滤** — 严格只保留人工智能领域论文，包括但不限于：机器学习、深度学习、神经网络、自然语言处理、计算机视觉、强化学习、知识表示、推理、规划、机器人学、多智能体系统等方向；优先选择 cs.AI 分类论文，可辅助选择 cs.LG（机器学习）、cs.CL（计算语言学）、cs.CV（计算机视觉）、cs.RO（机器人学）、cs.MA（多智能体系统）相关人工智能子领域
   - 完成标志：已移除所有非人工智能领域的论文

4. **去重检查** — 用 Read 读取 `paperReview/` 下所有历史 JSON 文件，按 arXiv ID 比对，排除已采集过的论文
   - 完成标志：每个候选已与所有历史数据比对

5. **撰写中文摘要** — 为每篇论文写中文核心摘要，格式为「研究主题 + 核心方法 + 主要贡献」
   - 完成标志：每篇论文都有一条符合公式的中文摘要

6. **排序取前** — 按提交日期降序排序，截取最新 Top 20
   - 完成标志：已排序且精确含 20 篇论文

7. **输出与存储** — 按以下 JSON 格式返回结果，用 `collected_at` 记录 ISO 8601 时间戳，并保存到 `paperReview/` 目录
   - 完成标志：输出已格式化并通过 JSON schema 校验，文件已成功保存

## 输出格式

```json
{
  "source": "arxiv-papers",
  "skill": "arxiv-papers",
  "collected_at": "2026-07-12T00:00:00Z",
  "items": [
    {
      "arxiv_id": "2407.12345",
      "title": "论文标题",
      "authors": ["作者1", "作者2"],
      "url": "https://arxiv.org/abs/2407.12345",
      "pdf_url": "https://arxiv.org/pdf/2407.12345",
      "chinese_summary": "研究主题 + 核心方法 + 主要贡献",
      "abstract": "英文原始摘要",
      "submitted_date": "2026-07-10",
      "categories": ["cs.AI", "cs.LG"],
      "keywords": ["关键词1", "关键词2"]
    }
  ]
}
```

- `items` 上限 20 条，按提交日期降序
- `chinese_summary` 中文，格式严格为「研究主题 + 核心方法 + 主要贡献」
- `categories` 包含 arXiv 分类标签
- 保存路径：`paperReview/arxiv-{date}.json`（date 格式 YYYYMMDD）

## 采集约束

- 仅通过 HTML 解析获取数据，不使用 arXiv API
- 输出 JSON 格式到 stdout，同时保存到 `paperReview/` 目录
- 执行时间必须小于 15 秒
- 失败时返回空数组，不进行去重
- **核心约束：仅采集人工智能领域论文，主要聚焦 cs.AI 分类，辅以 cs.LG、cs.CL、cs.CV、cs.RO、cs.MA 等人工智能相关子分类**
