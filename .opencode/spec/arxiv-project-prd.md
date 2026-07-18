# PRD: arXiv 人工智能论文采集与分析

## 1. 背景
- 现有项目已经具备 GitHub Trending 技术动态采集与分析能力，但缺少对学术研究论文的稳定追踪
- arXiv 是 AI 领域最新研究成果发布最及时的公开平台，适合作为每日论文发现入口
- 目标是在不引入复杂基础设施的前提下，形成一条可重复执行的论文采集、筛选、摘要和落盘流程

## 2. 产品目标
- 每日获取最新人工智能领域论文，帮助快速掌握研究动态
- 为每篇论文生成适合中文阅读的简明信息卡片
- 保持结构化输出，便于后续检索、摘要汇总和二次分析
- 与现有 Agent / Skill 架构兼容，支持分步骤执行与统一编排

## 3. 目标用户
- 需要追踪 AI 最新论文的开发者
- 需要快速筛选研究方向的技术负责人
- 需要从论文中提炼趋势和选题的研究人员

## 4. 使用场景
- 每日定时运行，生成当天最新 AI 论文清单
- 用户临时查询“今天有哪些多模态/Agent/推理方向的新论文”
- 为后续深度分析、周报汇总或知识库入库提供原始素材

## 5. 核心范围
### 5.1 输入
- arXiv 最新论文列表页
- 单篇论文详情页
- 既有历史结果文件，位于 `paperReview/`

### 5.2 输出
- 当日论文 JSON 文件，保存到 `paperReview/`
- 每篇论文包含基础元数据、英文摘要、中文摘要、研究方向和关键词

### 5.3 处理范围
- 优先采集 `cs.AI`
- 可扩展采集 `cs.LG`、`cs.CL`、`cs.CV`、`cs.RO`、`cs.MA`
- 仅保留人工智能领域强相关论文

## 6. 非目标
- 不做论文全文下载与解析
- 不做 PDF 内容抽取、图表理解与实验复现
- 不做用户权限管理
- 不做 Web 前端展示
- 不做复杂向量检索或推荐系统
- 不做实时通知、邮件或机器人推送

## 7. 功能需求
### 7.1 列表采集
- 从 arXiv 最新列表页读取候选论文
- 提取字段：`arxiv_id`、`title`、`authors`、`url`、`pdf_url`、`submitted_date`、`categories`
- 默认收集最新候选论文，供后续过滤至 Top 20

### 7.2 详情补全
- 逐篇访问论文详情页
- 提取字段：`abstract`
- 有评论或补充元数据时，可额外记录 `comments`

### 7.3 领域过滤
- 依据分类、标题和摘要判断是否属于人工智能领域
- 输出字段：`is_relevant`、`ai_subdomain`、`keywords`
- 剔除明显不相关论文

### 7.4 中文摘要生成
- 基于英文摘要生成中文摘要
- 摘要结构遵循“研究主题 + 核心方法 + 主要贡献”
- 摘要要求准确、精炼、便于快速阅读

### 7.5 结果管理
- 对结果按 `arxiv_id` 去重
- 与 `paperReview/` 历史文件比对，避免重复收录
- 按提交日期降序保留 Top 20
- 以标准 JSON 文件落盘

## 8. Agent / Skill 映射
| 阶段 | Agent | Skill | 职责 |
|------|-------|-------|------|
| 列表采集 | `arxiv_list_collector` | `arxiv-list-collector` | 获取候选论文列表 |
| 详情补全 | `arxiv_detail_collector` | `arxiv-detail-collector` | 补全摘要和元数据 |
| 领域过滤 | `arxiv_domain_filter` | `arxiv-domain-filter` | 判断 AI 相关性并分类 |
| 中文摘要 | `arxiv_summary_writer` | `arxiv-summary-writer` | 生成中文摘要 |
| 结果整理 | `arxiv_manager` | `arxiv-manager` | 去重、排序、保存 |
| 流程入口 | - | `arxiv-papers` | 编排完整流程 |

## 9. 数据格式
### 9.1 单篇论文对象
```json
{
  "arxiv_id": "2607.08745",
  "title": "AUTOPILOT VQA: Benchmarking Vision-Language Models for Incident-Centric Dashcam Understanding",
  "authors": ["Author A", "Author B"],
  "url": "https://arxiv.org/abs/2607.08745",
  "pdf_url": "https://arxiv.org/pdf/2607.08745",
  "abstract": "English abstract...",
  "chinese_summary": "中文摘要内容",
  "comments": "optional",
  "submitted_date": "2026-07-09",
  "categories": ["cs.AI", "cs.CV"],
  "is_relevant": true,
  "ai_subdomain": "多模态",
  "keywords": ["vision-language models", "VQA", "autonomous driving"]
}
```

### 9.2 每日结果文件
```json
{
  "source": "arxiv-papers",
  "skill": "arxiv-papers",
  "collected_at": "2026-07-12T00:00:00Z",
  "items": []
}
```

## 10. 输入输出样例
### 10.1 输入样例
- 列表页输入：`https://arxiv.org/list/cs.AI/recent`
- 详情页输入：`https://arxiv.org/abs/2607.08745`

### 10.2 输出样例
```json
{
  "arxiv_id": "2607.08745",
  "title": "AUTOPILOT VQA: Benchmarking Vision-Language Models for Incident-Centric Dashcam Understanding",
  "chinese_summary": "本论文提出面向行车记录仪场景的视觉问答基准，用于评估视觉语言模型对安全关键事件的理解和推理能力。",
  "ai_subdomain": "多模态",
  "keywords": ["vision-language models", "VQA", "safety evaluation"]
}
```

## 11. 目录约定
- Vision 文档：[arxivProjectVision.md](file:///home/ubuntu/ai-knowledge-base/.opencode/spec/arxivProjectVision.md)
- PRD 文档：`/home/ubuntu/ai-knowledge-base/.opencode/spec/arxiv-project-prd.md`
- Agents 目录：`/home/ubuntu/ai-knowledge-base/.opencode/agents/arxiv/`
- Skills 目录：`/home/ubuntu/ai-knowledge-base/.opencode/skills/arxiv/`
- 输出目录：`/home/ubuntu/ai-knowledge-base/paperReview/`

## 12. 失败处理策略
### 12.1 列表页获取失败
- 返回空结果，不中断整个系统
- 记录失败原因，便于重试和定位问题

### 12.2 单篇详情页获取失败
- 跳过当前论文，继续处理后续论文
- 保留最小基础字段，避免整批任务失败

### 12.3 摘要或分类缺失
- 将对应字段置为空或默认值
- 不编造内容，不用猜测替代真实信息

### 12.4 去重或落盘失败
- 输出阶段性结果供人工检查
- 明确错误位置，避免静默失败

## 13. 验收标准
- 每日任务能稳定抓取并输出 20 篇 AI 相关论文
- 输出 JSON 结构稳定且字段完整
- 中文摘要准确、通顺、无明显幻觉
- AI 子领域判断基本合理，可支撑后续主题筛选
- 历史去重逻辑有效，不重复收录同一论文

## 14. 未来扩展
- 增加按主题筛选，如多模态、智能体、推理、训练效率
- 增加论文评分与推荐优先级
- 增加周报/月报汇总能力
- 增加与 GitHub 项目分析结果的联合观察能力
