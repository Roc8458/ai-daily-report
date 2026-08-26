# 定时任务指令（实战版 task-prompt）

> 这是本项目在线上定时任务（每日 08:00，Asia/Shanghai）中**实际运行**的完整指令。
> 与 `SKILL.md` 的脚本化流程互补：脚本负责数据结构，本指令定义内容质量与产出规格。
> 使用时把占位符换成你自己的邮箱与 SMTP 授权码（授权码获取见 [smtp-guide.md](smtp-guide.md)）。
>
> ⚠️ 邮箱地址和授权码是私密凭据，只写进任务平台的配置或本地 `.env`，不要提交到任何公开仓库。

---

执行 AI 每日早报任务（自包含规格，每次执行都是全新环境，不依赖外部文件）：

【目标】抓取国内外 AI 资讯 → 生成完整日报（带摘要、小结、GitHub趋势）→ 通过 QQ SMTP 发送到 you@example.com → 汇报结果。

【步骤1 搭建环境】
```
mkdir -p /workspace/ai-daily/reports && cd /workspace/ai-daily
```
写入 .env：SMTP_HOST=smtp.qq.com、SMTP_PORT=465、SMTP_USER=you@example.com、SMTP_PASS=你的SMTP授权码、TO_EMAIL=you@example.com
```
pip3 install -q requests feedparser markdown
```

【步骤2 抓取资讯】国外约70%/国内约30%，覆盖六维度：模型技术/商业产业/资本巨头/政策治理/消费产品/具身智能。每源超时12秒、失败1次即放弃改用联网搜索（WebSearch，freshness=d2），不反复重试：
- 国外直抓（实测可通）：
  - TechCrunch AI https://techcrunch.com/category/artificial-intelligence/ （正则提取 href+标题）
  - The Verge AI RSS https://www.theverge.com/rss/ai-artificial-intelligence/index.xml （feedparser解析）
  - HN Algolia API https://hn.algolia.com/api/v1/search_by_date?query=AI+OR+LLM+OR+OpenAI+OR+Claude+OR+GPT+OR+agent&tags=story&hitsPerPage=40&numericFilters=points>20 （JSON解析，保留points和num_comments作为热度信号）
  - arXiv API http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10
- 不可达源改联网搜索：OpenAI/Anthropic 官方动态、Google AI Blog、AI 融资与资本市场（Nvidia/OpenAI/Anthropic/Google/Meta）、AI 政策监管（EU AI Act、加州SB53等）、Reddit r/MachineLearning 与 r/LocalLLaMA 热帖、GitHub Trending（WebSearch 搜「GitHub trending AI open source this week」含周增Star数）
- 国内直抓：量子位 RSS https://www.qbitai.com/feed （feedparser）、IT之家 RSS https://www.ithome.com/rss/ （feedparser+AI关键词过滤）、智东西 https://www.zhidx.com/ （正则）、雷锋网 https://www.leiphone.com/ （正则）、钛媒体 https://www.tmtpost.com/ （正则+AI过滤）

【步骤3 新闻挑选——按价值排序，不限来源】

重要：来源不重要，内容质量重要。不要因为某来源抓到多条就全收，也不要限制每源条数。挑选标准：

1. 六维度轮转均衡（技术/商业/资本/政策/产品/具身智能各维度轮流取条，避免全是模型发布）
2. 热度信号优先（HN帖子按points排序，有金额/百分比的新闻优先）
3. 国外精选约12-14条，国内精选约6条
4. 英文标题翻译为中文（保留专有名词原文）

【步骤4 生成日报——必须带完整摘要，不是骨架】

保存至 /workspace/ai-daily/reports/YYYY-MM-DD.md，结构：
1) 标题「🤖 AI 每日早报 · YYYY年MM月DD日（周X）」
2) 导语：列出实际抓取到的信息源名称，说明国外约70%/国内约30%，覆盖六维度
3) 国外动态（约12-14条）：每条格式：

   ```
   ### 序号. 【维度标签】中文标题
   2-3句中文摘要（含关键数据：金额、百分比、公司名；英文新闻需翻译标题+写中文摘要；
   不可达的源用WebSearch结果写摘要；摘要精炼，包含核心事实+一句行业意义，控制在50字以内）
   🔗 [前往 该条新闻的实际来源名 原文](https://实际链接)
   ```

4) 国内动态（约6条）：同上格式
5) GitHub 趋势：3-5个项目表格（项目名|周增Star|定位），附本周开源趋势总结
6) 今日小结：3-5条主线（每条2-3句）+ 📌行动提示（1-3条可执行建议）
7) 文末：信息来源说明 + 「仅供参考，不构成投资或决策建议」

关键格式要求：
- 链接文字必须动态显示该条新闻的实际来源名（哪条来自TechCrunch就显示TechCrunch，哪条来自The Verge就显示The Verge，哪条来自量子位就显示量子位），格式为「🔗 [前往 实际来源名 原文](url)」，绝不写死某个固定来源名
- 摘要必须实质性内容（2-3句，精炼），不能写「待Agent撰写」
- 金额/比例保留原始数字
- 六维度标签：【前沿模型与技术】【商业与产业】【资本市场与巨头】【政策与治理】【消费级与产品应用】【具身智能与物理AI】

【步骤5 发送邮件】

用 Python smtplib 发送 HTML 邮件：
- SMTP_SSL 连接 smtp.qq.com:465，登录 your-smtp-user / 你的SMTP授权码（通用邮箱的 HOST/端口 见 [smtp-guide.md](smtp-guide.md)）
- 邮件主题：🤖 AI 每日早报 · YYYY年MM月DD日
- 收件人：you@example.com
- HTML 正文：用 markdown 库把日报 Markdown 转为 HTML，套卡片式 CSS 样式（h3与blockquote之间18px间距、紫色左边框摘要块、虚线分节、表格圆角），样式参考 assets/sample-report-email.html
- 同时附纯文本降级版本
- 发件人显示名：AI 日报助手

【步骤6 汇报】

报告：发送成功/失败、主题、精选条数统计。某板块抓取失败仍生成其余板块不空跑；邮件发送失败记录一次即结束，严禁死循环重试。
