#!/usr/bin/env python3
"""AI 日报主流程：抓取 → 生成骨架 → 发送邮件
用法：
  python3 run_daily.py              # 完整流程（抓取+骨架+发送）
  python3 run_daily.py --no-send    # 只生成不发送（预览模式）
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
SCRIPTS = Path(__file__).parent


def main():
    no_send = "--no-send" in sys.argv
    now = datetime.now()
    date_file = now.strftime("%Y-%m-%d")
    raw_path = BASE / "reports" / f"{date_file}-raw.json"
    md_path = BASE / "reports" / f"{date_file}.md"
    (BASE / "reports").mkdir(parents=True, exist_ok=True)

    # 1. 抓取
    print("=" * 50)
    print(f"▶ [{now:%H:%M:%S}] 步骤 1/3：抓取信息源")
    print("=" * 50)
    r = subprocess.run([sys.executable, str(SCRIPTS / "fetch_news.py"),
                        "--out", str(raw_path)])
    if r.returncode != 0:
        print("❌ 抓取脚本执行失败")
        sys.exit(1)

    # 2. 生成骨架
    print("\n" + "=" * 50)
    print("▶ 步骤 2/3：生成日报骨架")
    print("=" * 50)
    r = subprocess.run([sys.executable, str(SCRIPTS / "generate_report.py"),
                        str(raw_path), "--out", str(md_path)])
    if r.returncode != 0:
        print("❌ 生成脚本执行失败")
        sys.exit(1)

    # 3. 发送
    if no_send:
        print("\n▶ --no-send 模式：跳过发送。日报在：" + str(md_path))
        return

    print("\n" + "=" * 50)
    print("▶ 步骤 3/3：发送邮件")
    print("=" * 50)
    r = subprocess.run([sys.executable, str(SCRIPTS / "send_report.py"), str(md_path)])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
