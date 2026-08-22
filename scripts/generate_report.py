#!/usr/bin/env python3
"""日报生成模块：把抓取的原料 JSON 组装成日报 Markdown 骨架
说明：本脚本生成「结构完整的骨架」（标题+链接+来源），
      中文摘要与深度小结建议由 Agent 在此基础上撰写润色——
      脚本管数据结构，Agent 管内容质量。
用法：
  python3 generate_report.py <raw_material.json> [--out reports/YYYY-MM-DD.md]
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

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


def build_report(data: dict, date_str: str) -> str:
    intl, cn = data.get("intl", []), data.get("cn", [])
    lines = []
    weekday = WEEKDAYS[datetime.now().weekday()]
    i_count, c_count = len(intl), len(cn)
    total = i_count + c_count

    lines.append(f"# 🤖 AI 每日早报 · {date_str}（周{weekday}）\n")
    lines.append(f"> **导语**：本期综合国内外多渠道信息源生成，国外内容约 70%、国内约 30%。"
                 f"共收录 {total} 条资讯，覆盖维度：模型技术、商业产业、资本巨头、政策治理、"
                 f"消费产品、具身智能。摘要与小结由 Agent 综合撰写。\n")
    lines.append("---\n")

    # 国外动态
    lines.append("## 一、国外动态\n")
    for it in intl:
        dim = classify(it["title"])
        meta = f"（{it['meta']}）" if it.get("meta") else ""
        lines.append(f"### 【{dim}】{it['title']}{meta}\n")
        lines.append(f"**摘要**：（待 Agent 撰写中文摘要）\n")
        lines.append(f"🔗 原文：[{it['source']}]({it['url']})\n")

    # 国内动态
    lines.append("## 二、国内动态\n")
    for it in cn:
        dim = classify(it["title"])
        lines.append(f"### 【{dim}】{it['title']}\n")
        lines.append(f"**摘要**：（待 Agent 撰写摘要）\n")
        lines.append(f"🔗 来源：[{it['source']}]({it['url']})\n")

    # GitHub 趋势（占位，由 Agent 联网搜索补充）
    lines.append("## 三、GitHub 趋势\n")
    lines.append("> （由 Agent 通过联网搜索补充本周热门 AI 项目，含周增 Star）\n")
    lines.append("| 项目 | 周增 Star | 定位 |\n|------|----------|------|\n| （待补充） | | |\n")

    # 小结（占位）
    lines.append("## 四、今日小结\n")
    lines.append("> **主线**：（待 Agent 提炼 3-5 条当日主线 + 行动提示）\n")
    lines.append("---\n")
    lines.append("*信息来源：TechCrunch、The Verge、Google AI Blog、Hacker News、arXiv、"
                 "量子位、智东西、雷锋网、IT之家、36氪、钛媒体等公开渠道，"
                 "综合联网检索生成。*\n")
    lines.append("*本报告仅供参考，不构成投资或决策建议。*\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI 日报骨架生成")
    parser.add_argument("raw", help="fetch_news.py 输出的原料 JSON 路径")
    parser.add_argument("--out", help="输出 Markdown 路径（默认 reports/今日.md）")
    args = parser.parse_args()

    data = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    date_str = datetime.now().strftime("%Y年%m月%d日")
    out_path = Path(args.out) if args.out else (
        Path(__file__).parent.parent / "reports" / f"{datetime.now():%Y-%m-%d}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(data, date_str)
    out_path.write_text(report, encoding="utf-8")
    print(f"✅ 日报骨架已生成 → {out_path}")
    print("   下一步：Agent 撰写摘要/小结后，用 send_report.py 发送")


if __name__ == "__main__":
    main()
