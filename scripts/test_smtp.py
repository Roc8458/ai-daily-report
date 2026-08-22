#!/usr/bin/env python3
"""SMTP 连通性测试
验证 .env 中的 SMTP 配置是否可用（连接 + 登录 + 可选试发）。
用法：
  python3 test_smtp.py            # 仅测试连接与登录
  python3 test_smtp.py --send     # 额外发一封测试邮件
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from send_report import load_config, validate_config, send_email

TEST_MD = """# SMTP 测试

这是一封 **ai-daily-report** 的 SMTP 配置测试邮件。

如果你收到了这封邮件，说明邮件链路已完全打通，可以开始接收每日 AI 日报了。
"""


def main():
    base = Path(__file__).parent.parent
    config = load_config()
    missing = validate_config(config)
    if missing:
        print("❌ 配置不完整：" + "、".join(missing))
        print(f"   请编辑 {base / '.env'}（参考 .env.example）")
        sys.exit(1)

    host = config["SMTP_HOST"]
    port = config.get("SMTP_PORT", "465")
    print(f"▶ 测试 SMTP 服务器 {host}:{port} …")

    if "--send" in sys.argv:
        try:
            to = send_email("✅ ai-daily-report SMTP 测试邮件", TEST_MD, config)
            print(f"✅ 连接、登录、发送全部成功！收件人：{', '.join(to)}")
            print("   请到收件箱（含垃圾箱）确认收到测试邮件。")
        except Exception as e:
            print(f"❌ 发送失败：{e}")
            sys.exit(1)
    else:
        from send_report import _connect
        try:
            with _connect(config) as server:
                server.login(config["SMTP_USER"], config["SMTP_PASS"])
            print("✅ 连接与登录成功！（如需完整验证请加 --send 参数试发一封）")
        except Exception as e:
            print(f"❌ 连接/登录失败：{e}")
            print("   常见原因：授权码错误、SMTP 服务未开启、端口被网络策略拦截")
            sys.exit(1)


if __name__ == "__main__":
    main()
