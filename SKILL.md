---
name: ai-daily-report
description: "AI Daily Report — automated multi-source AI news aggregation (11+ sources, 70% international / 30% China), 6-dimension classification, SMTP email delivery. Use when setting up AI daily digest, email newsletter automation, or news aggregation pipelines."
version: 1.1.0
author: WorkBuddy community
license: MIT
---

# AI Daily Report（AI 每日早报自动化）

> **中文 | [English](README.md)**

为用户搭建一套全自动 AI 日报系统：**每天定时抓取中外 AI 资讯 → 生成六维度日报 → 通过用户自己的 SMTP 邮箱投递**。全程云端运行，用户设备只需收邮件。

## Core Workflow / 核心工作流

搭建流程共 5 步：

```
1. Init environment       → bash scripts/setup.sh
2. Configure user SMTP    → edit .env (Agent NEVER fills auth codes)
3. Test email pipeline    → python3 scripts/test_smtp.py --send
4. Run a trial cycle      → python3 scripts/run_daily.py
5. Create scheduled task  → WorkBuddy automation (recommended) or system cron
```

## Steps / 步骤详解

### 1. Initialize / 初始化

```bash
bash scripts/setup.sh
```

Copies `.env.example` → `.env`, creates `reports/` and `logs/` dirs, installs Python deps (requests / feedparser / markdown).

### 2. Configure SMTP / 配置 SMTP

**SECURITY RULE: SMTP auth codes are private credentials. The Agent must NEVER fill them in — the user must edit `.env` themselves.**

Edit `.env` with just 3 required fields:

```ini
SMTP_USER=your-email@example.com
SMTP_PASS=your-smtp-auth-code
TO_EMAIL=your-email@example.com
```

SMTP host/port is auto-inferred from the email domain (QQ→smtp.qq.com:465, Gmail→smtp.gmail.com:587, etc.). Full provider guide: `references/smtp-guide.md`.

### 3. Test Pipeline / 测试链路

```bash
python3 scripts/test_smtp.py --send
```

Sends a test email. User confirms receipt — pipeline is live. Troubleshooting: `references/smtp-guide.md`.

### 4. Trial Run / 试跑一期

```bash
python3 scripts/run_daily.py
```

Full cycle: fetch → generate skeleton → send.

**Content Enhancement (important)**: `generate_report.py` produces a structural skeleton. The Agent should enhance:
- **Chinese summaries**: Write 2-3 sentence summaries for 12-18 key items across all dimensions. Translate English titles; use web search for unreachable sources (OpenAI/Anthropic blogs, Reddit, GitHub trending, financial media) — max 1 retry per source
- **Daily Takeaway**: Distill 3-5 key themes + actionable insights for readers

Format spec: `references/report-format.md`.

### 5. Scheduled Task / 定时任务

**Option A: WorkBuddy / CodeBuddy (recommended, cloud-based)**

> Execute ai-daily-report daily task: check environment → run `scripts/run_daily.py` → supplement with web search for summaries & GitHub trends → report results. Single source failure doesn't block the pipeline; email failure is logged once, never retried in a loop.

**Option B: Local cron**

```bash
crontab -e
0 8 * * * cd /path/to/ai-daily-report && python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

## Source Architecture / 信息源架构

| Category | Direct Fetch (tested) | Web Search Fallback |
|----------|----------------------|-------------------|
| International ~70% | TechCrunch AI, The Verge AI RSS, Google AI Blog, arXiv cs.AI, HN Algolia API | OpenAI/Anthropic official, Reddit, GitHub trending, Bloomberg/Reuters |
| China ~30% | QbitAI, Zhidx, Leiphone, IT之家, 36Kr, TMTPost (AI-filtered) | Major financing/policy supplements |

Full source list: `references/sources.md`. Any failed source is replaced by web search — never blocks the pipeline.

## Project Structure / 目录结构

```
ai-daily-report/
├── SKILL.md               ← This file
├── README.md              ← English documentation
├── README_CN.md           ← Chinese documentation
├── .env.example           ← SMTP config template (user copies to .env)
├── scripts/
│   ├── setup.sh           ← One-click init
│   ├── fetch_news.py      ← Multi-source fetcher (outputs raw JSON)
│   ├── generate_report.py ← Report skeleton generator (Agent enhances)
│   ├── send_report.py     ← SMTP sender (SSL/STARTTLS adaptive)
│   ├── run_daily.py       ← Main pipeline orchestrator
│   └── test_smtp.py       ← SMTP connectivity test
├── references/
│   ├── smtp-guide.md      ← Auth codes & troubleshooting
│   ├── sources.md         ← Source list & network strategy
│   └── report-format.md   ← Report format spec (6 dimensions)
└── assets/
    └── sample-report.md   ← Sample report
```

## Security / 安全须知

- `.env` (containing auth codes) is in `.gitignore` — **never commit to any public repo**
- Auth codes are separate from login passwords — reset anytime in email settings
- Multi-user deployments: use a dedicated sender email
