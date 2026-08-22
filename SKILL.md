---
name: ai-daily-report
description: AI 每日早报自动化 skill - 多源抓取国内外 AI 资讯（国外约70%/国内约30%），生成覆盖技术/商业/资本/政策/产品/具身智能六维度的日报，通过用户自配的 SMTP 邮箱（QQ/163/Gmail 等）云端投递。当用户想要搭建 AI 日报、每日资讯邮件推送、新闻聚合自动化时使用。SMTP 授权码由用户自己配置，skill 不内置任何凭据。
version: 1.0.0
author: WorkBuddy community
license: MIT
---

# AI Daily Report（AI 每日早报自动化）

为用户搭建一套全自动 AI 日报系统：**每天定时抓取中外 AI 资讯 → 生成六维度日报 → 通过用户自己的 SMTP 邮箱投递**。全程云端运行，用户设备只需收邮件。

## 核心工作流

搭建流程共 5 步：

```
1. 初始化环境          → bash scripts/setup.sh
2. 配置用户 SMTP       → 引导用户编辑 .env（绝不能代填授权码）
3. 测试邮件链路        → python3 scripts/test_smtp.py --send
4. 试跑一期验证        → python3 scripts/run_daily.py
5. 创建定时任务        → WorkBuddy 自动化（推荐）或系统 cron
```

## 步骤详解

### 1. 初始化

```bash
bash scripts/setup.sh
```

脚本会复制 `.env.example` 为 `.env`、创建 `reports/` 与 `logs/` 目录、安装依赖（requests / feedparser / markdown）。

### 2. 配置 SMTP（用户自己的凭据）

**关键原则：SMTP 授权码是用户私密凭据，必须由用户本人填写，Agent 不得代填、不得在对话中索要后写入公开文件。**

引导用户编辑 `.env`，最少只需填 3 项：

```ini
SMTP_USER=用户的邮箱
SMTP_PASS=用户的SMTP授权码
TO_EMAIL=收件邮箱（发给自己则与 SMTP_USER 相同）
```

SMTP host/port 会按邮箱域名自动推断（QQ→smtp.qq.com:465、Gmail→smtp.gmail.com:587 等）。各邮箱授权码获取方式见 `references/smtp-guide.md`。

### 3. 测试链路

```bash
python3 scripts/test_smtp.py --send
```

会发一封测试邮件，用户确认收到后链路即打通。失败排查见 `references/smtp-guide.md` 的「常见故障」章节。

### 4. 试跑一期

```bash
python3 scripts/run_daily.py
```

完整执行「抓取 → 生成骨架 → 发送」。

**内容质量增强（重要）**：`generate_report.py` 生成的是结构骨架（标题+链接+分类），Agent 应主动补足两类内容：
- **中文摘要**：对重点条目（按维度均衡挑选 12-18 条）撰写 2-3 句中文摘要。英文新闻需翻译标题；不可达的源（OpenAI/Anthropic 官方博客、Reddit、GitHub trending、财经媒体）直接用 WebSearch 联网检索最新动态补充，每源最多重试 1 次
- **今日小结**：提炼 3-5 条当日主线 + 给读者的行动提示

格式规范详见 `references/report-format.md`。

### 5. 定时任务

**方式 A：WorkBuddy / CodeBuddy 自动化（推荐，全程云端）**

通过 automation-task-manager 创建每日 08:00 任务，prompt 模板：

> 执行 ai-daily-report 日报任务：检查 `<skill 安装目录>` 环境完整性（缺失则按 SKILL.md 重建）→ 运行 `scripts/run_daily.py` 抓取并发送 → 对重点条目用联网搜索补充摘要与 GitHub 趋势 → 汇报发送结果。某板块抓取失败仍生成其余板块；邮件发送失败记录一次即结束，严禁死循环重试。

**方式 B：本地 cron（用户自己的服务器）**

```bash
crontab -e
# 每天早上 8 点执行（记得用绝对路径）
0 8 * * * cd /path/to/ai-daily-report && python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

## 信息源架构

| 类别 | 直抓（实测可通） | 联网搜索兜底 |
|------|----------------|-------------|
| 国外 ~70% | TechCrunch AI、The Verge AI RSS、Google AI Blog、arXiv cs.AI、HN Algolia API | OpenAI/Anthropic 官方、Reddit、GitHub trending、Bloomberg/Reuters 等财经媒体 |
| 国内 ~30% | 量子位、智东西、雷锋网、IT之家、36氪、钛媒体（AI 过滤） | 补充搜索当日重大融资/政策 |

完整清单与抓取策略见 `references/sources.md`。任何源失败 1 次即转联网搜索，不阻塞整体流程。

## 目录结构

```
ai-daily-report/
├── SKILL.md               ← 本文件
├── README.md              ← 完整使用文档（GitHub 发布版）
├── .env.example           ← SMTP 配置模板（用户复制为 .env）
├── scripts/
│   ├── setup.sh           ← 一键初始化
│   ├── fetch_news.py      ← 多源抓取（输出原料 JSON）
│   ├── generate_report.py ← 生成日报骨架（Agent 再润色）
│   ├── send_report.py     ← SMTP 通用发送（SSL/STARTTLS 自适应）
│   ├── run_daily.py       ← 主流程编排
│   └── test_smtp.py       ← SMTP 链路测试
├── references/
│   ├── smtp-guide.md      ← 各邮箱授权码获取与故障排查
│   ├── sources.md         ← 信息源清单与网络策略
│   └── report-format.md   ← 日报格式规范（六维度）
└── assets/
    └── sample-report.md   ← 日报效果示例
```

## 安全须知

- `.env`（含授权码）已被 `.gitignore` 排除，**永远不要提交到任何公开仓库**
- 授权码与登录密码不同，可随时在邮箱设置中重置
- 多用户/团队部署时建议使用子邮箱或专用发件邮箱
