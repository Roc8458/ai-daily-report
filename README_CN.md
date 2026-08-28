# 🤖 AI Daily Report · AI 每日早报自动化

> **中文 | [English](README.md)**

每两天一期（隔日），北京时间早上 8 点，一份覆盖**技术 / 商业 / 资本 / 政策 / 产品 / 具身智能**六维度的 AI 日报，自动出现在你的邮箱里。

**全程云端运行**——多源抓取 → 智能编排 → 你的 SMTP 邮箱投递。你的电脑不需要开机。

[![License: MIT](https://img.shields.io/badge/License-MIT-4f46e5.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab.svg)](https://www.python.org/)

---

## 效果预览

每天收到的邮件长这样（HTML 排版）：

- **国外动态 ~60%**（约 15 条）：OpenAI / Anthropic / Google / Meta / Nvidia 的模型、融资、IPO、组织变动；EU AI 法案等政策监管；LinkedIn / Gemini / Meta AI 等产品动态
- **国内动态 ~40%**（约 10 条）：大模型商业化、具身智能与机器人大会、垂类 AI 融资、DeepSeek 等国产模型动态
- **GitHub 趋势**：本周最火的 AI 开源项目（含周增 Star）
- **今日小结**：3-5 条主线提炼 + 给读者的行动提示

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🌍 **中外配比** | 国外约 60% / 国内约 40%（15 条 / 10 条），默认均衡覆盖六维度 |
| 📡 **10 直抓源** | TechCrunch / The Verge / Google AI Blog / HN / arXiv / 量子位 / 智东西 / 雷锋网 / IT之家 / 钛媒体 |
| 🔎 **检索补充** | 政策、资本等维度由 Google News RSS 自动补位，不空跑 |
| 📈 **GitHub 趋势** | 直抓 GitHub Trending 周榜（仓库 + 周增 Star），趋势表不再空缺 |
| 📝 **基于正文的摘要** | 并发抓取候选文章正文喂给 LLM——摘要有真实内容，不再复述标题 |
| ✅ **两阶段 LLM 管线** | 阶段1 按价值选稿（维度轮转、时效过滤）；阶段2 基于正文写作；产出程序化校验，不达标自动反馈重写 |
| 📧 **SMTP 通用** | QQ / 163 / Gmail / Outlook / Foxmail / 企业邮箱……授权码全部用户自配 |
| 🎨 **邮件排版** | 卡片式 HTML 邮件 + 纯文本降级，标题分级、表格、链接可点击 |
| ☁️ **云端定时** | GitHub Actions（每日 08:00）/ WorkBuddy / CodeBuddy，也支持本地 cron |
| 🔒 **安全设计** | `.env` 默认 gitignore，云端凭据走 GitHub Secrets |

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 一个开启了 SMTP 服务的邮箱（QQ / 163 / Gmail / Outlook 等均可）

### 三步搭建

```bash
# 1️⃣ 克隆 & 初始化
git clone https://github.com/Roc8458/ai-daily-report.git
cd ai-daily-report
bash scripts/setup.sh

# 2️⃣ 配置你的 SMTP（编辑 .env，只需填 3 项）
vim .env
```

```ini
SMTP_USER=你的邮箱@qq.com
SMTP_PASS=你的SMTP授权码
TO_EMAIL=你的邮箱@qq.com
```

<details>
<summary><b>📋 各邮箱 SMTP 授权码获取方式（点击展开）</b></summary>

| 邮箱 | SMTP 地址 | 授权码获取 |
|------|-----------|-----------|
| QQ 邮箱 | smtp.qq.com:465 | 设置 → 账号 → 开启 SMTP 服务 → 生成授权码 |
| 163 邮箱 | smtp.163.com:465 | 设置 → POP3/SMTP → 开启服务 → 设置授权码 |
| 126 邮箱 | smtp.126.com:465 | 同 163 |
| Gmail | smtp.gmail.com:587 | Google 账号 → 安全 → 应用专用密码 |
| Outlook | smtp-mail.outlook.com:587 | 账号安全 → 应用密码 |
| Foxmail | smtp.qq.com:465 | 同 QQ 邮箱 |
| 腾讯企业邮箱 | smtp.exmail.qq.com:465 | 管理后台 → 客户端专用密码 |

完整指南：[references/smtp-guide.md](references/smtp-guide.md)

</details>

```bash
# 3️⃣ 测试 + 试跑
python3 scripts/test_smtp.py --send    # 发一封测试邮件验证链路
python3 scripts/run_daily.py           # 完整跑一期
```

收到邮件就成功了 🎉

## ⏰ 定时运行

### 方式 A：GitHub Actions（推荐）

仓库自带 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)——**每两天一期**，发行日北京时间 08:00（UTC 00:00）全程云端运行，电脑不用开机。需在仓库 Settings 配置：

| Secret / Variable | 说明 |
|-------------------|------|
| `SMTP_USER` / `SMTP_PASS` / `TO_EMAIL` | SMTP 账号、授权码、收件邮箱 |
| `LLM_API_KEY`（secret） | 任意 OpenAI 兼容大模型的 API Key |
| `LLM_BASE_URL`（variable，可选） | 默认 `https://api.xiaomimimo.com/v1` |
| `LLM_MODEL`（variable，可选） | 默认 `mimo-v2.5` |

手动测试：Actions → AI Daily Report → Run workflow → 勾选「仅测试，不发邮件」。

> 注：GitHub Actions 定时触发在高峰期可能有几十分钟到数小时的漂移。

### 方式 B：WorkBuddy / CodeBuddy 自动化

> 创建每日 08:00 定时任务：执行 ai-daily-report 日报流程——检查环境、抓取信息源、生成日报、发送邮件、汇报结果。

### 方式 C：本地 cron

```bash
crontab -e
# 每天早上 8 点
0 8 * * * cd /path/to/ai-daily-report && python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

## 📖 日报格式规范

```
🤖 AI 每日早报 · YYYY年MM月DD日（周X）
├── 导语（实际信源 + 比例 + 当日主线）
├── 一、国外动态（约 15 条：维度标签 + 中文标题 + 基于正文的摘要 + 原文链接）
├── 二、国内动态（约 10 条，同上格式）
├── 三、GitHub 趋势（5-8 个项目表格，含周增 Star + 开源趋势总结）
├── 四、今日小结（3-5 条主线 + 📌行动提示）
└── 五、信息来源说明（+ 免责声明）
```

**六维度**：前沿模型与技术 / 商业与产业 / 资本市场与巨头 / 政策与治理 / 消费级与产品应用 / 具身智能与物理 AI

完整规范：[references/report-format.md](references/report-format.md)

## ⚙️ 高级配置

`.env` 全部可选项：

```ini
# ---- 必填 3 项 ----
SMTP_USER=你的邮箱@qq.com
SMTP_PASS=你的SMTP授权码
TO_EMAIL=你的邮箱@qq.com

# ---- 可选（留空则自动推断）----
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_SSL=1
SENDER_NAME=AI 日报助手
MAIL_SUBJECT_PREFIX=🤖 AI 每日早报
```

### 信息源选择

```bash
python3 scripts/fetch_news.py --intl techcrunch,hackernews --cn qbitai,zhidx
```

## 🧩 工作原理

```
fetch_news.py → 原料 JSON（10 直抓源 + Google News 检索补位
                + GitHub Trending 周榜 + 并发正文抓取）
       ↓
generate_report.py → Markdown 骨架（六维度分类，兜底输出）
       ↓
enhance_report.py 两阶段 LLM：
  阶段1 选稿——按价值排序、维度轮转、时效过滤
  阶段2 写作——基于文章正文写完整日报
  校验——标题/五节/条数/表格程序化检查，不达标反馈重写一次
       ↓
send_report.py → HTML 邮件（SMTP 发送）
```

**脚本管数据结构，LLM 管内容质量**——这是本项目的设计哲学。

## 📁 目录结构

```
ai-daily-report/
├── SKILL.md               ← Hermes/WorkBuddy 技能定义
├── README.md              ← 英文版文档
├── README_CN.md           ← 本文件（中文版）
├── .env.example           ← SMTP 配置模板
├── scripts/
│   ├── setup.sh           ← 一键初始化
│   ├── fetch_news.py      ← 多源抓取（直抓+检索补位+Trending+正文抓取）
│   ├── generate_report.py ← 日报骨架生成（兜底）
│   ├── enhance_report.py  ← 两阶段 LLM 增强（选稿+写作+校验）
│   ├── send_report.py     ← SMTP 邮件发送（SSL/STARTTLS 自适应）
│   ├── run_daily.py       ← 主流程编排
│   └── test_smtp.py       ← SMTP 链路测试
├── references/
│   ├── smtp-guide.md      ← 授权码获取与故障排查
│   ├── sources.md         ← 信息源清单与网络策略
│   ├── report-format.md   ← 日报格式规范
│   └── task-prompt.md     ← 实战定时任务指令（线上运行版完整规格）
└── assets/
    ├── sample-report.md         ← 日报效果示例（Markdown）
    └── sample-report-email.html ← 邮件效果示例（卡片式 HTML）
```

## ❓ 常见问题

<details>
<summary><b>邮件发送失败 / 收不到？</b></summary>

1. 跑 `python3 scripts/test_smtp.py` 看具体报错
2. 授权码错误 → 重新生成（不是邮箱登录密码！）
3. 检查垃圾箱
4. 465 端口被拦截 → 换 587 端口

</details>

<details>
<summary><b>可以发给多个收件人吗？</b></summary>

可以，`TO_EMAIL` 用英文逗号分隔：`TO_EMAIL=a@qq.com,b@163.com`

</details>

<details>
<summary><b>授权码安全吗？</b></summary>

授权码只存在本地 `.env`（已被 `.gitignore` 排除）。它是独立于登录密码的专用凭据，可随时重置。

</details>

## 📄 License

[MIT](LICENSE) — 自由使用、修改、分发。
