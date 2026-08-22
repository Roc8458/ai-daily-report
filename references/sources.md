# 信息源清单与网络策略

## 设计原则

1. **每源超时 12 秒，失败 1 次即放弃**——立即改用联网搜索（WebSearch）兜底，不重试、不等待
2. **国外约 70% / 国内约 30%**——以实际可获取的高质量信息为准，不强行凑数
3. **单源故障不影响整体**——某板块全挂仍生成其余板块

## 国外源（约 70%）

### 直抓（脚本内置，实测可通）

| 源 | 通道 | 说明 |
|----|------|------|
| TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/` | 商业/融资/产品动态主力源 |
| The Verge AI | RSS：`https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | 产品与行业深度 |
| Google AI Blog | `https://blog.google/technology/ai/` | 官方一手（Gemini/Waymo/DeepMind 动态） |
| Hacker News | Algolia API（`hn.algolia.com`，主站被墙时的替代通道） | 社区热度信号（points>20 过滤） |
| arXiv cs.AI | 官方 API，按提交时间倒序 | 论文速递 |

### 联网搜索兜底（Agent 执行）

不可达或无 RSS 的源，直接用 WebSearch 检索最新标题与摘要：

- OpenAI Blog / Anthropic News（官方动态）
- Reddit r/MachineLearning、r/LocalLLaMA（社区信号）
- GitHub Trending（周榜 + 周增 Star）
- Bloomberg / Reuters / CNBC / FT（财经与巨头动向）
- MIT Technology Review / VentureBeat / Ars Technica / BAIR Blog

## 国内源（约 30%）

### 直抓（脚本内置）

| 源 | 通道 | 说明 |
|----|------|------|
| 量子位 | RSS：`https://www.qbitai.com/feed` | 中文 AI 媒体，技术与产业兼顾 |
| 智东西 | `https://www.zhidx.com/` 首页解析 | 智能产业深度 |
| 雷锋网 | `https://www.leiphone.com/` 首页解析 | AI 商业报道 |
| IT之家 | RSS：`https://www.ithome.com/rss/` + AI 关键词过滤 | 快讯类，覆盖面广 |
| 36氪 | RSS：`https://36kr.com/feed` + AI 过滤 | 融资与创投 |
| 钛媒体 | `https://www.tmtpost.com/` + AI 过滤 | 产业观察 |

> InfoQ 中国为 JS 渲染页面，直抓不稳定，建议 Agent 联网搜索补充。

## 内容维度均衡

抓取原料后按六维度打标签（`generate_report.py` 内置关键词分类器），编排时注意：

- 前沿模型与技术 ✅ 保持覆盖但不必占主导
- 商业与产业 / 资本市场与巨头 ✅ 与技术类大致均衡
- 政策与治理、消费级产品、具身智能 ✅ 有则必收

**避免整份报告都是论文/模型发布。**

## 质量红线

- 所有链接必须真实可点击（来自抓取结果或搜索结果，不得凭记忆编造）
- 金额、百分比、时间保留原始数字
- 国内条目优先标注一手来源
