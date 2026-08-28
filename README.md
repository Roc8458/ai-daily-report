# 🤖 AI Daily Report

> **[中文](README_CN.md) | English**

Automated AI news digest — fetches **10 direct sources plus search supplements** covering global and Chinese AI developments, generates a **6-dimension report**, and delivers it to your inbox via your own SMTP email.

**Runs 100% in the cloud** — your computer doesn't need to be on.

[![License: MIT](https://img.shields.io/badge/License-MIT-4f46e5.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab.svg)](https://www.python.org/)

---

## Preview

Every morning you receive an HTML email like this:

- **International (~70%)**: OpenAI / Anthropic / Google / Meta / Nvidia — models, funding, IPOs, org changes; EU AI Act and policy; LinkedIn / Gemini / Meta AI product updates
- **China (~30%)**: Domestic LLM commercialization, robotics & embodied AI, vertical AI funding, DeepSeek and other Chinese model dynamics
- **GitHub Trends**: Weekly hottest AI open-source repos (with star growth)
- **Daily Takeaway**: 3–5 key themes + actionable insights

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌍 **Global + China** | ~70% international / ~30% Chinese, balanced across 6 dimensions |
| 📡 **10 Direct Sources** | TechCrunch, The Verge, Google AI Blog, HN, arXiv, QbitAI, Zhidx, Leiphone, IT之家, TMTPost |
| 🔎 **Search Supplement** | Policy/funding dimensions auto-filled via Google News RSS when direct fetch is thin |
| 📈 **GitHub Trending** | Weekly trending board scraped directly (repo + weekly star growth), table never empty |
| 📝 **Content-Based Summaries** | Article bodies fetched concurrently and fed to the LLM — summaries are written from real content, not headlines |
| ✅ **Two-Stage LLM Pipeline** | Stage 1 selects news by value with dimension rotation; Stage 2 writes the report from article content; output is programmatically validated with one feedback-retry round |
| 📧 **Universal SMTP** | QQ / 163 / Gmail / Outlook / Foxmail / corporate email — all supported |
| 🎨 **HTML Email** | Card-style HTML + plain-text fallback, clickable links |
| ☁️ **Cloud Scheduling** | GitHub Actions (daily 08:00 CST), WorkBuddy/CodeBuddy, or local cron |
| 🔒 **Secure** | `.env` gitignored, credentials in GitHub Secrets |

## 🚀 Quick Start

### Requirements

- Python 3.8+
- An email account with SMTP enabled (QQ / 163 / Gmail / Outlook / any provider)

### 3-Step Setup

```bash
# 1️⃣ Clone & init
git clone https://github.com/Roc8458/ai-daily-report.git
cd ai-daily-report
bash scripts/setup.sh

# 2️⃣ Configure your SMTP (edit .env — only 3 fields needed)
vim .env
```

```ini
SMTP_USER=you@example.com       # Your email
SMTP_PASS=your-smtp-password    # SMTP auth code (NOT your login password)
TO_EMAIL=you@example.com        # Recipient (comma-separated for multiple)
```

<details>
<summary><b>📋 SMTP auth code by provider</b></summary>

| Provider | SMTP Server | How to get auth code |
|----------|------------|---------------------|
| QQ Mail | smtp.qq.com:465 | Settings → Account → Enable SMTP → Generate auth code |
| 163 Mail | smtp.163.com:465 | Settings → POP3/SMTP → Enable → Set auth code |
| 126 Mail | smtp.126.com:465 | Same as 163 |
| Gmail | smtp.gmail.com:587 | Google Account → Security → App passwords |
| Outlook | smtp-mail.outlook.com:587 | Account security → App passwords |
| Foxmail | smtp.qq.com:465 | Same as QQ Mail |
| Tencent Exmail | smtp.exmail.qq.com:465 | Admin console → Client-specific password |

Full guide: [references/smtp-guide.md](references/smtp-guide.md)

</details>

```bash
# 3️⃣ Test & run
python3 scripts/test_smtp.py --send    # Send a test email
python3 scripts/run_daily.py           # Run a full cycle
```

Check your inbox 🎉

## ⏰ Scheduling

### Option A: GitHub Actions (Recommended)

The repo ships with [`.github/workflows/daily.yml`](.github/workflows/daily.yml) — runs daily at 08:00 Beijing time (UTC 00:00) entirely in the cloud. Configure these repository secrets/variables:

| Secret / Variable | Value |
|-------------------|-------|
| `SMTP_USER` / `SMTP_PASS` / `TO_EMAIL` | SMTP account, auth code, recipient |
| `LLM_API_KEY` (secret) | API key of any OpenAI-compatible LLM |
| `LLM_BASE_URL` (variable, optional) | Default `https://api.xiaomimimo.com/v1` |
| `LLM_MODEL` (variable, optional) | Default `mimo-v2.5` |

Manual test runs: Actions → AI Daily Report → Run workflow → check "test only (no email)".

> Note: GitHub Actions scheduled runs can drift by tens of minutes to a few hours under queue load.

### Option B: WorkBuddy / CodeBuddy

> Create a daily task at 08:00: run the ai-daily-report pipeline — check environment, fetch sources, generate report, send email, report results.

### Option C: Local cron

```bash
crontab -e
# Every day at 8 AM (server timezone)
0 8 * * * cd /path/to/ai-daily-report && python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

## 📖 Report Format

```
🤖 AI Daily Report · YYYY-MM-DD (Day of Week)
├── Intro (sources used + source ratio + dimensions covered)
├── I. International News (12–14 numbered items: dimension tag + Chinese title + content-based summary + link)
├── II. China News (5–7 items, same format)
├── III. GitHub Trends (5–8 repos table with weekly star growth + weekly open-source recap)
├── IV. Daily Takeaway (3–5 themes + 📌 action items)
└── V. Source Notes (+ disclaimer)
```

**6 Dimensions**: Frontier Models & Tech · Business & Industry · Capital & Giants · Policy & Governance · Consumer Products · Embodied AI & Robotics

Full spec: [references/report-format.md](references/report-format.md)

## ⚙️ Configuration

All options in `.env`:

```ini
# ---- Required (3 fields) ----
SMTP_USER=you@example.com
SMTP_PASS=your-smtp-password
TO_EMAIL=you@example.com

# ---- Optional (auto-inferred if omitted) ----
SMTP_HOST=smtp.example.com    # Inferred from email domain
SMTP_PORT=465                 # 465=SSL, 587=STARTTLS
SMTP_SSL=1                    # 1=SSL, 0=STARTTLS
SENDER_NAME=AI Daily Report   # Display name
MAIL_SUBJECT_PREFIX=🤖 AI Daily Report
```

### Source Selection

```bash
python3 scripts/fetch_news.py --intl techcrunch,hackernews --cn qbitai,zhidx
```

## 🧩 How It Works

```
fetch_news.py → raw JSON (10 direct sources + Google News supplement
                 + GitHub Trending weekly board + concurrent article-body fetch)
       ↓
generate_report.py → Markdown skeleton (6-dimension classified, fallback output)
       ↓
enhance_report.py (two-stage LLM):
  stage 1 — select news by value, dimension rotation, freshness
  stage 2 — write the full report from article content
  validation — format check (title/5 sections/counts/table), one feedback-retry
       ↓
send_report.py → HTML email via SMTP
```

**Scripts handle data structure; LLM handles content quality** — that's the design philosophy.

## 📁 Project Structure

```
ai-daily-report/
├── SKILL.md               ← Hermes/WorkBuddy skill definition
├── README.md              ← This file (English)
├── README_CN.md           ← Chinese version
├── .env.example           ← SMTP config template
├── scripts/
│   ├── setup.sh           ← One-click init
│   ├── fetch_news.py      ← Multi-source fetcher (direct + search supplement + trending + body fetch)
│   ├── generate_report.py ← Report skeleton generator (fallback)
│   ├── enhance_report.py  ← Two-stage LLM enhancement (select + write + validate)
│   ├── send_report.py     ← SMTP sender (SSL/STARTTLS adaptive)
│   ├── run_daily.py       ← Main pipeline
│   └── test_smtp.py       ← SMTP connectivity test
├── references/
│   ├── smtp-guide.md      ← Auth code guide & troubleshooting
│   ├── sources.md         ← Source list & network strategy
│   ├── report-format.md   ← Report format spec
│   └── task-prompt.md     ← Battle-tested scheduled-task prompt (v1.2 cloud spec)
└── assets/
    ├── sample-report.md        ← Sample report (Markdown)
    └── sample-report-email.html ← Sample HTML email (card style)
```

## ❓ FAQ

<details>
<summary><b>Email not sending / not received?</b></summary>

1. Run `python3 scripts/test_smtp.py` for detailed error
2. Wrong auth code → regenerate (it's NOT your login password!)
3. Check spam folder
4. Port 465 blocked (common in corporate networks) → use port 587

</details>

<details>
<summary><b>Can I send to multiple recipients?</b></summary>

Yes — comma-separated in `TO_EMAIL`: `TO_EMAIL=a@example.com,b@example.com`

</details>

<details>
<summary><b>Is the auth code secure?</b></summary>

Stored only in your local `.env` (gitignored). It's separate from your login password and can be reset anytime in email settings.

</details>

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.
