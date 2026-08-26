#!/usr/bin/env python3
"""日报增强模块：调用 LLM（OpenAI 兼容接口）把「抓取原料 JSON + 骨架提示」变成完整日报。

设计：
  脚本管数据结构（抓取、发送），LLM 管内容质量（挑选、翻译、摘要、小结）。
  无 LLM_API_KEY 时优雅跳过（保留骨架，流程不断）。

环境变量：
  LLM_API_KEY   必填（缺失则跳过增强）
  LLM_BASE_URL  默认 https://api.xiaomimimo.com/v1 （OpenAI 兼容）
  LLM_MODEL     默认 mimo-v2.5

用法：
  python3 enhance_report.py <raw.json> <skeleton.md> --out reports/YYYY-MM-DD.md
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.xiaomimimo.com/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "mimo-v2.5")

SYSTEM_PROMPT = """你是一名 AI 行业资深编辑，负责把抓取到的原始资讯加工成一份中文《AI 每日早报》邮件。
规则：
1. 新闻挑选按价值排序：六维度轮转均衡（前沿模型与技术/商业与产业/资本市场与巨头/政策与治理/消费级与产品应用/具身智能与物理AI），有金额、百分比、热度信号（HN points）的优先；不因某来源条数多就多收。
2. 国外精选约 12-14 条，国内精选约 6 条。宁缺毋滥，凑不满就少收。
3. 每条格式：
   ### 【维度标签】中文标题（英文标题翻译为中文，保留专有名词原文）
   2-3 句中文摘要，含关键数据（金额/百分比/公司名），50 字以内，精炼不空话。
   🔗 原文：[来源名](该条的原始链接) ← 链接必须原样复制候选清单里的 url，一字不改。
4. 不编造：候选清单里没有的信息绝不出现。GitHub 趋势一节仅当候选里有 GitHub 项目数据时写表格，否则整节省略并注明「本期未采集到趋势数据」。
5. 今日小结：提炼 3-5 条当日主线（每条 2-3 句）+ 📌行动提示 1-3 条。
6. 输出直接是完整 Markdown 正文（以 # 标题行开头），不要代码块包裹，不要任何解释。"""


def build_user_prompt(raw: dict, date_str: str) -> str:
    def fmt(items, region):
        out = []
        for i, it in enumerate(items):
            meta = f" | {it['meta']}" if it.get("meta") else ""
            title = (it.get("title") or "").replace("\n", " ").strip()[:200]
            out.append(f"- [{region}-{i}] 来源:{it.get('source','')}{meta}\n  标题:{title}\n  链接:{it.get('url','')}")
        return "\n".join(out)

    intl, cn = raw.get("intl", []), raw.get("cn", [])
    return f"""请生成 {date_str} 的《AI 每日早报》完整 Markdown。

【候选资讯 · 国外 {len(intl)} 条】
{fmt(intl, 'INTL')}

【候选资讯 · 国内 {len(cn)} 条】
{fmt(cn, 'CN')}"""


def valid_urls(raw: dict) -> set:
    urls = set()
    for k in ("intl", "cn"):
        for it in raw.get(k, []):
            if it.get("url"):
                urls.add(it["url"].rstrip("/"))
    return urls


def main():
    parser = argparse.ArgumentParser(description="LLM 日报增强")
    parser.add_argument("raw", help="fetch_news.py 输出的原料 JSON")
    parser.add_argument("skeleton", help="generate_report.py 生成的骨架（当前未使用，保留参数兼容管线）")
    parser.add_argument("--out", required=True, help="最终日报输出路径")
    args = parser.parse_args()

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        # 优雅降级：无 key 时把骨架原样作为产出，流程不断
        skeleton = Path(args.skeleton)
        out_path.write_text(skeleton.read_text(encoding="utf-8"), encoding="utf-8")
        print("⚠️ 未设置 LLM_API_KEY，跳过 LLM 增强（输出为骨架版）")
        return 0

    from datetime import datetime
    date_str = datetime.now().strftime("%Y年%m月%d日")
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    allowed = valid_urls(raw)

    resp = None
    for attempt in (1, 2):  # 失败重试一次，严禁死循环
        try:
            r = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_user_prompt(raw, date_str)},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 8192,
                },
                timeout=300,
            )
            r.raise_for_status()
            resp = r.json()
            break
        except Exception as e:
            print(f"⚠️ LLM 调用失败（第{attempt}次）：{e}")
            if attempt == 1:
                time.sleep(10)

    if not resp:
        skeleton = Path(args.skeleton)
        out_path.write_text(skeleton.read_text(encoding="utf-8"), encoding="utf-8")
        print("❌ LLM 两连败，降级输出骨架版")
        return 1

    text = resp["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("markdown"):
            text = text[len("markdown"):]

    # 校验链接没有被模型篡改
    import re
    found = {m.group(2).rstrip("/") for m in re.finditer(r"\[([^\]]*)\]\((https?://[^)]+)\)", text)}
    bad = found - allowed if allowed else set()
    if bad:
        print(f"⚠️ 发现 {len(bad)} 个不在候选清单中的链接（可能是模型幻觉）：")
        for u in list(bad)[:5]:
            print(f"   {u}")

    out_path.write_text(text + "\n", encoding="utf-8")
    finish = resp["choices"][0].get("finish_reason", "?")
    usage = resp.get("usage", {})
    print(f"✅ LLM 增强完成 → {out_path}")
    print(f"   模型={resp.get('model', MODEL)} finish={finish} tokens={usage.get('total_tokens', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
