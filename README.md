# 🤖 AI Daily Report · AI 每日早报自动化

> 每天早上 8 点，一份覆盖**技术 / 商业 / 资本 / 政策 / 产品 / 具身智能**六维度的 AI 日报，自动出现在你的邮箱里。

**全程云端运行**——多源抓取 → 智能编排 → 你的 SMTP 邮箱投递。你的电脑不需要开机。

[![License: MIT](https://img.shields.io/badge/License-MIT-4f46e5.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-WorkBuddy%20%7C%20CodeBuddy%20%7C%20Cron-ff6f00.svg)](#定时运行)

---

## 效果预览

每天收到的邮件长这样（HTML 排版，详见 [assets/sample-report.md](assets/sample-report.md)）：

- **国外动态 ~70%**：OpenAI / Anthropic / Google / Meta / Nvidia 的模型、融资、IPO、组织变动；EU AI 法案等政策监管；LinkedIn / Gemini / Meta AI 等产品动态
- **国内动态 ~30%**：大模型商业化、具身智能与机器人大会、垂类 AI 融资、DeepSeek 等国产模型动态
- **GitHub 趋势**：本周最火的 AI 开源项目（含周增 Star）
- **今日小结**：3-5 条主线提炼 + 给读者的行动提示

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🌍 **中外配比** | 国外约 70% / 国内约 30%，默认均衡覆盖六维度 |
| 📡 **多源聚合** | 11+ 信息源直抓（TechCrunch / The Verge / Google AI Blog / HN / arXiv / 量子位 / 智东西 / 雷锋网 / IT之家 / 36氪 / 钛媒体），内置 HN 被墙时的 Algolia 替代通道 |
| 🔎 **搜索兜底** | 抓取失败的源自动转联网搜索（Agent 模式），每源最多重试 1 次，不空跑 |
| 📧 **SMTP 通用** | QQ / 163 / 126 / Gmail / Outlook / Foxmail / 企业邮箱……授权码全部用户自配，**skill 不内置任何凭据** |
| 🎨 **邮件排版** | 卡片式 HTML 邮件 + 纯文本降级，标题分级、表格、链接可点击 |
| ☁️ **云端定时** | 一键接入 WorkBuddy / CodeBuddy 自动化（每日 08:00），也支持本地 cron |
| 🔒 **安全设计** | `.env` 默认 gitignore，授权码永不入库 |

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 一个开启了 SMTP 服务的邮箱（QQ / 163 / Gmail 等均可）

### 三步搭建

```bash
# 1️⃣ 克隆 & 初始化
git clone https://github.com/<你的用户名>/ai-daily-report.git
cd ai-daily-report
bash scripts/setup.sh

# 2️⃣ 配置你的 SMTP（编辑 .env，只需填 3 项）
vim .env
```

```ini
SMTP_USER=123456789@qq.com      # 你的邮箱
SMTP_PASS=你的SMTP授权码         # 获取方式见下表
TO_EMAIL=123456789@qq.com       # 收件邮箱（可多个，逗号分隔）
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
| 企业微信邮箱 | smtp.exmail.qq.com:465 | 管理后台 → 客户端专用密码 |

完整指南与故障排查：[references/smtp-guide.md](references/smtp-guide.md)

</details>

```bash
# 3️⃣ 测试 + 试跑
python3 scripts/test_smtp.py --send    # 发一封测试邮件验证链路
python3 scripts/run_daily.py           # 完整跑一期，检查邮箱
```

收到邮件就成功了 🎉

## ⏰ 定时运行

### 方式 A：WorkBuddy / CodeBuddy 自动化（推荐，全程云端）

在有 automation-task-manager 能力的环境里，直接让 Agent 创建定时任务：

> 帮我创建一个每天早上 8 点的定时任务：执行 ai-daily-report 日报流程——检查项目环境、抓取信息源、生成日报、发送邮件到我的邮箱，完成后汇报结果。

任务模板与 prompt 见 [SKILL.md](SKILL.md) 第 5 步。

### 方式 B：本地 cron / 服务器 crontab

```bash
crontab -e
# 每天早上 8 点（服务器时区）
0 8 * * * cd /path/to/ai-daily-report && python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

## 📖 日报格式规范

```
AI 每日早报 · 日期
├── 导语（信息源比例与本期覆盖维度）
├── 一、国外动态（~12条：维度标签 + 中文标题 + 摘要 + 可点击原文链接）
├── 二、国内动态（~6条：标签 + 标题 + 摘要 + 来源）
├── 三、GitHub 趋势（3-5 个项目表格，含周增 Star）
└── 四、今日小结（3-5 条主线 + 行动提示）
```

六维度覆盖：**前沿模型与技术 / 商业与产业 / 资本市场与巨头 / 政策与治理 / 消费级与产品应用 / 具身智能与物理 AI**。完整规范见 [references/report-format.md](references/report-format.md)。

## ⚙️ 高级配置

`.env` 全部可选项：

```ini
# ---- 必填 3 项 ----
SMTP_USER=you@example.com
SMTP_PASS=your-smtp-password
TO_EMAIL=you@example.com

# ---- 可选（有默认值）----
SMTP_HOST=smtp.qq.com     # 不填则按邮箱域名自动推断
SMTP_PORT=465             # 465=SSL，587=STARTTLS（自动适配）
SMTP_SSL=1                # 1=SSL，0=STARTTLS
SENDER_NAME=AI 日报助手    # 发件人显示名
MAIL_SUBJECT_PREFIX=🤖 AI 每日早报
```

信息源开关（编辑 `scripts/fetch_news.py` 的 `INTL_FETCHERS` / `CN_FETCHERS` 字典，或运行时 `--intl` / `--cn` 参数指定）：

```bash
python3 scripts/fetch_news.py --intl techcrunch,hackernews --cn qbitai,zhidx
```

## 🧩 与纯脚本日报的区别

直接跑 `run_daily.py` 得到的是「结构骨架 + 原料」；在 **Agent 环境（WorkBuddy / CodeBuddy / Claude Code 等）** 中使用本 skill 时，Agent 会：

1. 用联网搜索补齐不可达源（OpenAI 官方博客、Reddit、GitHub trending、财经媒体）
2. 为重点条目撰写中文摘要（英文新闻自动翻译标题）
3. 提炼当日主线，生成有观点的「今日小结」与行动提示

**脚本管数据结构，Agent 管内容质量**——这是本 skill 的设计哲学。

## ❓ FAQ

<details>
<summary><b>邮件发送失败 / 收不到？</b></summary>

1. 跑 `python3 scripts/test_smtp.py` 看具体报错
2. 授权码错误 → 重新生成（不是邮箱登录密码！）
3. 检查垃圾箱
4. 部分内网环境会拦截 465 端口 → 换 587 端口（Gmail/Outlook 默认）

</details>

<details>
<summary><b>某天没收到日报？</b></summary>

查看 `logs/daily.log`。常见原因：信息源全部超时（网络波动）、SMTP 授权码被重置、定时任务被暂停。设计上「单板块失败不影响整体」——除非邮件链路本身故障，日报不会完全空跑。

</details>

<details>
<summary><b>可以发给多个收件人吗？</b></summary>

可以，`TO_EMAIL` 用英文逗号分隔：`TO_EMAIL=a@qq.com,b@163.com`

</details>

<details>
<summary><b>授权码安全吗？会泄露吗？</b></summary>

授权码只存在你本地的 `.env`（已被 `.gitignore` 排除）。它是独立于登录密码的专用凭据，可随时在邮箱设置中重置作废。**请勿将 `.env` 提交到任何公开仓库。**

</details>

## 📄 License

[MIT](LICENSE) — 自由使用、修改、分发。

---

<p align="center">如果这个项目对你有用，欢迎 ⭐ Star 支持</p>
