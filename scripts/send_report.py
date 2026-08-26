#!/usr/bin/env python3
"""AI 日报邮件发送模块（SMTP 通用版）
支持 QQ / 163 / 126 / Gmail / Outlook 等任意 SMTP 服务商，配置全部来自 .env。
安全提示：授权码（SMTP_PASS）只存在本地 .env，请勿提交到任何公开仓库。
"""
import re
import ssl
import smtplib
import sys
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# 常见邮箱 SMTP 预设（用户 .env 只写 PROVIDER 也可自动推断）
SMTP_PRESETS = {
    "qq": {"host": "smtp.qq.com", "port": 465, "ssl": True},
    "163": {"host": "smtp.163.com", "port": 465, "ssl": True},
    "126": {"host": "smtp.126.com", "port": 465, "ssl": True},
    "gmail": {"host": "smtp.gmail.com", "port": 587, "ssl": False},  # STARTTLS
    "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "hotmail": {"host": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "foxmail": {"host": "smtp.qq.com", "port": 465, "ssl": True},
    "sina": {"host": "smtp.sina.com", "port": 465, "ssl": True},
    "sohu": {"host": "smtp.sohu.com", "port": 465, "ssl": True},
    "aliyun": {"host": "smtp.qiye.aliyun.com", "port": 465, "ssl": True},
    "tencent_exmail": {"host": "smtp.exmail.qq.com", "port": 465, "ssl": True},
}


def load_config(env_path=None):
    """加载配置：.env 文件优先，缺失的字段从环境变量回退（GitHub Actions 场景）"""
    import os
    base = Path(env_path) if env_path else Path(__file__).parent.parent / ".env"
    config = {}
    if base.exists():
        for line in base.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()

    # 环境变量回退：只填充 .env 中没有的键
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASS",
                "TO_EMAIL", "SENDER_NAME", "MAIL_SUBJECT_PREFIX"):
        env_val = os.environ.get(key, "").strip()
        if env_val and not config.get(key):
            config[key] = env_val

    # .env 和环境变量都没有 → 视为无配置
    if not config:
        return None

    # 未显式配置 host/port 时按邮箱域名推断
    if "SMTP_HOST" not in config:
        domain = config.get("SMTP_USER", "").split("@")[-1].lower()
        preset_key = next((k for k in SMTP_PRESETS if k in domain), None)
        if preset_key:
            config["SMTP_HOST"] = SMTP_PRESETS[preset_key]["host"]
            config["SMTP_PORT"] = str(SMTP_PRESETS[preset_key]["port"])
            config["SMTP_SSL"] = "1" if SMTP_PRESETS[preset_key]["ssl"] else "0"
        else:
            config["SMTP_HOST"] = f"smtp.{domain}"
            config["SMTP_PORT"] = "465"
            config["SMTP_SSL"] = "1"
    return config


def validate_config(config):
    """校验必填项，返回缺失字段列表"""
    if config is None:
        return [".env 文件不存在（请复制 .env.example 为 .env 并填写）"]
    missing = []
    for key in ("SMTP_USER", "SMTP_PASS", "TO_EMAIL"):
        v = config.get(key, "")
        if not v or v.startswith("你的") or "xxx" in v.lower() or v == "":
            missing.append(key)
    return missing


def md_to_html(md_text: str) -> str:
    """Markdown（日报子集）→ 排版邮件 HTML"""
    try:
        import markdown
        body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    except ImportError:
        # 无 markdown 库时退化为 <pre>
        body = f"<pre style='white-space:pre-wrap;'>{md_text}</pre>"

    css = """
    <style>
      body { margin:0; padding:0; background:#f4f6f8; font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif; }
      .wrap { max-width:760px; margin:0 auto; padding:24px 16px; }
      .card { background:#fff; border-radius:12px; padding:28px 32px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
      h1 { font-size:22px; color:#1a1a2e; border-bottom:3px solid #4f46e5; padding-bottom:10px; margin-top:0; }
      h2 { font-size:18px; color:#4f46e5; margin-top:32px; margin-bottom:8px; padding:10px 14px; background:#eef2ff; border-radius:8px; }
      h3 { font-size:15.5px; color:#1a1a2e; margin:0 0 8px; line-height:1.6; }
      blockquote { margin:18px 0; padding:14px 18px; background:#f8fafc; border-left:4px solid #7c3aed; color:#475569; font-size:14px; line-height:1.85; border-radius:0 8px 8px 0; }
      p { font-size:14px; line-height:1.85; color:#334155; margin:14px 0; }
      a { color:#1a73e8; text-decoration:none; }
      table { width:100%; border-collapse:collapse; margin:18px 0; font-size:13.5px; }
      th { background:#4f46e5; color:#fff; padding:10px 12px; text-align:left; }
      td { padding:10px 12px; border-bottom:1px solid #e2e8f0; color:#334155; }
      tr:nth-child(even) td { background:#f8fafc; }
      hr { border:none; border-top:1px dashed #cbd5e1; margin:28px 0; }
      li { font-size:14px; line-height:1.85; color:#334155; margin:6px 0; }
      .footer { text-align:center; color:#94a3b8; font-size:11px; margin-top:18px; }
    </style>"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{css}</head>
<body><div class="wrap"><div class="card">{body}</div>
<p class="footer">由 ai-daily-report 自动生成投递 · Powered by WorkBuddy / CodeBuddy</p>
</div></body></html>"""


def md_to_text(md_text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", md_text)
    text = re.sub(r"[#*`>|]", "", text)
    return text


def _connect(config):
    """按 SSL/STARTTLS 建立连接"""
    host = config["SMTP_HOST"]
    port = int(config.get("SMTP_PORT", 465))
    use_ssl = config.get("SMTP_SSL", "1") == "1"
    ctx = ssl.create_default_context()
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
    server = smtplib.SMTP(host, port, timeout=30)
    server.starttls(context=ctx)
    return server


def send_email(subject: str, md_text: str, config: dict) -> list:
    """发送邮件，返回收件人列表"""
    smtp_user = config["SMTP_USER"]
    to_emails = [e.strip() for e in config["TO_EMAIL"].split(",") if e.strip()]
    sender_name = config.get("SENDER_NAME", "AI 日报助手")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(sender_name, "utf-8")), smtp_user))
    msg["To"] = ", ".join(to_emails)
    msg.attach(MIMEText(md_to_text(md_text), "plain", "utf-8"))
    msg.attach(MIMEText(md_to_html(md_text), "html", "utf-8"))

    with _connect(config) as server:
        server.login(smtp_user, config["SMTP_PASS"])
        server.sendmail(smtp_user, to_emails, msg.as_string())
    return to_emails


def main():
    md_path = sys.argv[1] if len(sys.argv) > 1 else "--latest"
    base = Path(__file__).parent.parent
    config = load_config()

    missing = validate_config(config)
    if missing:
        print("❌ 配置不完整：" + "、".join(missing))
        print(f"   请编辑 {base / '.env'}（参考 .env.example 与 references/smtp-guide.md）")
        sys.exit(1)

    # 定位报告文件
    if md_path == "--latest":
        reports = sorted((base / "reports").glob("*.md"))
        if not reports:
            print("❌ reports/ 目录下没有日报文件")
            sys.exit(1)
        md_path = reports[-1]
    else:
        md_path = Path(md_path)
        if not md_path.exists():
            print(f"❌ 文件不存在: {md_path}")
            sys.exit(1)

    md_text = Path(md_path).read_text(encoding="utf-8")
    m = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", md_text)
    date_str = m.group(1) if m else datetime.now().strftime("%Y年%m月%d日")
    subject = config.get("MAIL_SUBJECT_PREFIX", "🤖 AI 每日早报") + " · " + date_str

    to = send_email(subject, md_text, config)
    print(f"✅ 日报已发送：{subject}")
    print(f"   收件人：{', '.join(to)}")
    print(f"   来源文件：{md_path}")


if __name__ == "__main__":
    main()
