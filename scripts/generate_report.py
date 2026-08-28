#!/usr/bin/env python3
"""日报生成模块：把抓取的原料 JSON 组装成日报 Markdown 骨架
说明：本脚本生成「结构完整的兜底骨架」（标题+链接+可用的摘要片段），
     正式内容由 enhance_report.py 的两阶段 LLM 管线撰写——
     脚本管数据结构，LLM 管内容质量。
用法：
  python3 generate_report.py <raw_material.json> [--out reports/YYYY-MM-DD.md]
"""
import json
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

CN_TZ = timezone(timedelta(hours=8))
WEEKDAYS = "一二三四五六日"

# 六维度分类关键词（用于自动打标签）
DIMENSION_KEYWORDS = {
    "前沿模型与技术": ["model", "llm", "gpt", "claude", "gemini", "paper", "arxiv",
                    "release", "open-source", "模型", "论文", "开源", "训练", "推理"],
    "商业与产业": ["revenue", "ipo", "business", "enterprise", "adoption", "customer",
                "commercial", "营收", "商业化", "企业", "客户", "落地"],
    "资本市场与巨头": ["raise", "funding", "valuation", "billion", "million", "invest",
                   "merger", "acquisition", "融资", "估值", "投资", "并购", "股价"],
    "政策与治理": ["regulation", "law", "act", "policy", "compliance", "safety",
                "ethics", "ban", "监管", "法案", "政策", "合规", "安全", "伦理"],
    "消费级与产品应用": ["app", "launch", "feature", "user", "product", "assistant",
                   "hardware", "发布", "上线", "产品", "用户", "助手"],
    "具身智能与物理 AI": ["robot", "autonomous", "driving", "waymo", "embodied",
                    "manufacturing", "机器人", "自动驾驶", "具身", "智能制造"],
}


def classify(title: str) -> str:
    t = title.lower()
    scores = {dim: sum(1 for k in kws if k in t) for dim, kws in DIMENSION_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "商业与产业"


def _brief(it: dict) -> str:
    """兜底骨架里尽量带上摘要片段，而不是「待撰写」"""
    text = it.get("content") or it.get("summary") or ""
    if not text:
        return "（LLM 增强不可用，本条无摘要；详情见原文）"
    return text[:150] + ("…" if len(text) > 150 else "")


def build_report(data: dict, date_full: str) -> str:
    intl, cn = data.get("intl", []), data.get("cn", [])
    trending = data.get("github_trending", [])
    lines = []

    lines.append(f"# 🤖 AI 每日早报 · {date_full}\n")
    lines.append("> **导语**：本期综合国内外多渠道信息源生成，国外内容约 60%、国内约 40%。"
                 f"共收录 {len(intl) + len(cn)} 条资讯，覆盖维度：模型技术、商业产业、资本巨头、政策治理、"
                 "消费产品、具身智能。摘要与小结由 LLM 综合撰写。\n")
    lines.append("---\n")

    lines.append("## 一、国外动态\n")
    for n, it in enumerate(intl, 1):
        dim = classify(it["title"])
        meta = f"（{it['meta']}）" if it.get("meta") else ""
        lines.append(f"### {n}. 【{dim}】{it['title']}{meta}\n")
        lines.append(f"{_brief(it)}\n")
        lines.append(f"🔗 [前往 {it['source']} 原文]({it['url']})\n")

    lines.append("## 二、国内动态\n")
    for n, it in enumerate(cn, 1):
        dim = classify(it["title"])
        lines.append(f"### {n}. 【{dim}】{it['title']}\n")
        lines.append(f"{_brief(it)}\n")
        lines.append(f"🔗 [前往 {it['source']} 原文]({it['url']})\n")

    lines.append("## 三、GitHub 趋势\n")
    if trending:
        lines.append("| 项目 | 本周新增 Star | 定位 |")
        lines.append("|------|----------|------|")
        for t in trending:
            star = t.get("meta", "").replace("周增 ", "").replace(" Star", "")
            lines.append(f"| [{t['title']}]({t['url']}) | +{star} | {t.get('desc', '')} |")
        lines.append("")
    else:
        lines.append("本期未采集到趋势数据。\n")

    lines.append("## 四、今日小结\n")
    lines.append("> **主线**：（LLM 增强不可用，详见上方条目）\n")

    lines.append("## 五、信息来源说明\n")
    lines.append("*信息来源：TechCrunch、The Verge、Google AI Blog、Hacker News、arXiv、"
                 "量子位、智东西、雷锋网、IT之家、钛媒体等直抓渠道，部分维度由联网检索补充，"
                 "GitHub 趋势来自 GitHub Trending 周榜。*\n")
    lines.append("*⚠️ 本文仅供参考，不构成投资或决策建议。*\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI 日报骨架生成")
    parser.add_argument("raw", help="fetch_news.py 输出的原料 JSON 路径")
    parser.add_argument("--out", help="输出 Markdown 路径（默认 reports/今日.md）")
    args = parser.parse_args()

    data = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    now = datetime.now(CN_TZ)
    date_full = f"{now:%Y年%m月%d日}（周{WEEKDAYS[now.weekday()]}）"
    out_path = Path(args.out) if args.out else (
        Path(__file__).parent.parent / "reports" / f"{now:%Y-%m-%d}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(data, date_full)
    out_path.write_text(report, encoding="utf-8")
    print(f"✅ 日报骨架已生成 → {out_path}")
    print("   下一步：enhance_report.py 两阶段 LLM 撰写正式内容")


if __name__ == "__main__":
    main()
