#!/usr/bin/env python3
"""日报增强模块：两阶段 LLM 管线，把「抓取原料 JSON」变成完整日报。

设计：
  阶段1 选稿：全部候选（标题+摘要片段）交给 LLM 按价值挑选，输出编号；
  阶段2 写作：仅把选中条目的正文/摘要喂给 LLM，按 WorkBuddy 版格式写完整日报；
  程序化校验格式（标题/五节/条数/表格），不达标把问题清单喂回重写一次。
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
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.xiaomimimo.com/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "mimo-v2.5")

CN_TZ = timezone(timedelta(hours=8))
WEEKDAYS = "一二三四五六日"

DIMENSIONS = ("前沿模型与技术", "商业与产业", "资本市场与巨头", "政策与治理",
              "消费级与产品应用", "具身智能与物理AI")

# ---------- 阶段1：选稿 ----------

SELECT_SYSTEM = """你是新闻选稿主编。根据候选清单（编号 [I*] 为国外、[C*] 为国内）挑选当日日报条目。
挑选标准（按优先级）：
1. AI 相关性：主题必须围绕 AI/大模型/智能体/具身智能/算力/AI 政策；普通科技、地方赛事、无 AI 主线的选稿不选。
2. 时效性：只选近两日的资讯；明显是旧闻（周年回顾、旧项目重发）的不选。
3. 内容价值：有具体金额/百分比/模型发布/产品上线/政策动向的优先；纯观点稿、内容空洞的靠后。
4. 六维度轮转均衡（前沿模型与技术/商业与产业/资本市场与巨头/政策与治理/消费级与产品应用/具身智能与物理AI），避免某类新闻霸版。
5. 热度信号：HN 分数高的优先。
6. 国外选 12-14 条，国内选 5-7 条；同一事件的多来源报道只选信息最全的一条。
7. 宁缺毋滥：凑不满就少选。
只输出 JSON，不要任何解释：
{"intl": [编号数字...], "cn": [编号数字...]}"""


def fmt_candidates(items, prefix):
    out = []
    for i, it in enumerate(items):
        meta = f" | {it['meta']}" if it.get("meta") else ""
        brief = it.get("summary") or it.get("content") or ""
        brief = brief[:180] + ("…" if len(brief) > 180 else "")
        title = (it.get("title") or "").replace("\n", " ").strip()[:150]
        line = f"- [{prefix}{i}] 来源:{it.get('source','')}{meta}\n  标题:{title}"
        if brief:
            line += f"\n  摘要片段:{brief}"
        out.append(line)
    return "\n".join(out)


def parse_selection(text, n_intl, n_cn):
    """从 LLM 输出解析选中编号。多级容错：
    1) 标准 JSON {"intl":[..],"cn":[..]}
    2) 带标签行（国外/intl 后跟数字列表）
    3) 顺序兜底：文本中第一组数字为国外、第二组为国内
    返回 (intl_idx, cn_idx)"""
    def clamp(nums, bound):
        return [x for x in nums if 0 <= x < bound]

    m = re.search(r'"intl"\s*:\s*\[([^\]]*)\]', text)
    j = re.search(r'"cn"\s*:\s*\[([^\]]*)\]', text)
    if m and j:
        return (clamp([int(x) for x in re.findall(r"\d+", m.group(1))], n_intl),
                clamp([int(x) for x in re.findall(r"\d+", j.group(1))], n_cn))

    label = re.search(r'(?:国外|intl|INTL|I\s*组)\D{0,10}((?:\d+\s*[,，、\s]+)*\d+)', text)
    label_cn = re.search(r'(?:国内|cn|CN|C\s*组)\D{0,10}((?:\d+\s*[,，、\s]+)*\d+)', text)
    if label and label_cn:
        return (clamp([int(x) for x in re.findall(r"\d+", label.group(1))], n_intl),
                clamp([int(x) for x in re.findall(r"\d+", label_cn.group(1))], n_cn))

    groups = re.findall(r"\d+(?:\s*[,，、]\s*\d+){3,}", text)
    if groups:
        return (clamp([int(x) for x in re.findall(r"\d+", groups[0])], n_intl),
                clamp([int(x) for x in re.findall(r"\d+", groups[1])], n_cn) if len(groups) > 1 else [])
    return [], []


def heuristic_select(items, want):
    """LLM 选稿失败时的确定性兜底：有正文者优先、HN 热度加权，并按来源轮转
    （每组内按分排序、组间轮转取条），避免单一来源霸版。"""
    def score(it):
        s = 2 if (it.get("summary") or it.get("content")) else 0
        m = re.search(r"HN (\d+)", it.get("meta", ""))
        if m:
            s += min(int(m.group(1)) / 50, 3)
        return s

    by_source = {}
    for i, it in enumerate(items):
        by_source.setdefault(it.get("source", "?"), []).append(i)
    queues = [sorted(idx, key=lambda i: score(items[i]), reverse=True)
              for idx in by_source.values()]
    queues.sort(key=len, reverse=True)
    picked = []
    while len(picked) < want and any(queues):
        for q in queues:
            if q and len(picked) < want:
                picked.append(q.pop(0))
    return picked


# ---------- 阶段2：写作 ----------

WRITE_SYSTEM = """你是一名 AI 行业资深编辑，把精选资讯加工成一份中文《AI 每日早报》邮件，输出完整 Markdown。

输出结构（严格遵守，五个小节名一字不差）：

# 🤖 AI 每日早报 · {日期}（周X）
（X 由用户消息给出）
> **导语**：2-3 句。列出本期实际使用的信源名称，说明国外约 70%/国内约 30%、覆盖六维度，并用一句话点出当日主线。

## 一、国外动态
（12-14 条，每条格式：
### 序号. 【维度标签】中文标题
2-3 句中文摘要：核心事实（含金额/百分比/公司名/产品名等关键数据）+ 一句行业意义，50-90 字，禁止空话、禁止复述标题。英文标题翻译为中文，保留专有名词原文。
🔗 [前往 来源名 原文](链接)）
链接必须原样复制候选清单里的 url，一字不改；来源名用该条的来源。

## 二、国内动态
（5-7 条，格式同上）

## 三、GitHub 趋势
| 项目 | 本周新增 Star | 定位 |
|------|----------|------|
（用提供的趋势数据填 5-8 行；项目列写成带链接的仓库名，定位列用一句本质概括。表格后附一段「**本周开源趋势总结：**」2-3 句。若用户消息未提供趋势数据，本节只写一句「本期未采集到趋势数据」。）

## 四、今日小结
（3-5 条当日主线，每条 2-3 句，带编号；随后：
📌 行动提示
- 1-3 条可执行建议，分别面向开发者/产品者/决策者）

## 五、信息来源说明
（一段话列出全部信源，说明 GitHub 趋势来自 GitHub Trending 周榜抓取、部分维度由联网检索补充；末行加：
⚠️ 本文仅供参考，不构成投资或决策建议。）

硬性规则：
1. 六维度标签只用：【前沿模型与技术】【商业与产业】【资本市场与巨头】【政策与治理】【消费级与产品应用】【具身智能与物理AI】。
2. 摘要必须基于候选提供的「内容/摘要」撰写；资料里没有的数字、事件绝不能编造。
3. 同一事件只出现一次，不同小节不得重复。
4. 直接输出完整 Markdown 正文（以 # 标题行开头），不要代码块包裹，不要任何解释。"""


def build_write_prompt(date_full, selected_intl, selected_cn, trending):
    def block(items, prefix):
        out = []
        for i, it in enumerate(items):
            meta = f" | {it['meta']}" if it.get("meta") else ""
            title = (it.get("title") or "").replace("\n", " ").strip()[:200]
            out.append(f"- [{prefix}{i}] 来源:{it.get('source','')}{meta}")
            out.append(f"  标题:{title}")
            out.append(f"  链接:{it.get('url','')}")
            content = it.get("content") or it.get("summary") or ""
            if content:
                out.append(f"  内容:{content[:1200]}")
            out.append("")
        return "\n".join(out)

    parts = [f"请生成 {date_full} 的《AI 每日早报》完整 Markdown。\n",
             f"【精选 · 国外 {len(selected_intl)} 条】\n{block(selected_intl, 'I')}\n"]
    parts.append(f"【精选 · 国内 {len(selected_cn)} 条】\n{block(selected_cn, 'C')}\n")
    if trending:
        t_lines = []
        for t in trending:
            star = t.get("meta", "").replace("周增 ", "").replace(" Star", "")
            t_lines.append(f"- {t['title']} | 周增 {star} Star | {t.get('desc','')}")
            t_lines.append(f"  链接:{t.get('url','')}")
        parts.append("【GitHub Trending 周榜】\n" + "\n".join(t_lines) + "\n")
    else:
        parts.append("【GitHub Trending 周榜】本期未采集到趋势数据。\n")
    return "\n".join(parts)


# ---------- LLM 调用 ----------

def call_llm(messages, max_tokens, temperature, timeout=180, retries=2):
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    resp = None
    for attempt in (1, 2):
        if attempt > retries:
            break
        try:
            r = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=timeout)
            r.raise_for_status()
            resp = r.json()
            break
        except Exception as e:
            print(f"⚠️ LLM 调用失败（第{attempt}次）：{e}")
            if attempt < retries:
                time.sleep(10)
    return resp


# ---------- 校验 ----------

def _section(md, start, end):
    m = re.search(rf"## {start}.*?(?=\n## {end}|\Z)", md, re.S)
    return m.group(0) if m else ""


def validate_report(md, has_trending):
    """程序化格式校验，返回问题清单（空 = 通过）"""
    problems = []
    md = md.strip()
    if not re.match(r"#\s*🤖 AI 每日早报 · \d{4}年\d{1,2}月\d{1,2}日（周.）", md):
        problems.append("标题行必须是「# 🤖 AI 每日早报 · YYYY年MM月DD日（周X）」格式")
    if "导语" not in md:
        problems.append("缺少「导语」引用块")
    for sec in ("一、国外动态", "二、国内动态", "三、GitHub 趋势", "四、今日小结", "五、信息来源说明"):
        if not re.search(rf"##\s*{re.escape(sec)}", md):
            problems.append(f"缺少小节「## {sec}」")
    sec1 = _section(md, "一、国外动态", "二、国内动态")
    sec2 = _section(md, "二、国内动态", "三、GitHub 趋势")
    sec3 = _section(md, "三、GitHub 趋势", "四、今日小结")
    n1 = len(re.findall(r"^###\s*\d+\.\s*【", sec1, re.M))
    n2 = len(re.findall(r"^###\s*\d+\.\s*【", sec2, re.M))
    if n1 < 10:
        problems.append(f"「一、国外动态」只有 {n1} 条，需 10-14 条")
    if n2 < 4:
        problems.append(f"「二、国内动态」只有 {n2} 条，需 5-7 条")
    rows = [l for l in sec3.splitlines() if l.strip().startswith("|")]
    if has_trending and len(rows) < 5:
        problems.append(f"「三、GitHub 趋势」表格只有 {max(len(rows) - 2, 0)} 行数据，需 5-8 行")
    if "📌 行动提示" not in md:
        problems.append("「四、今日小结」末尾缺少「📌 行动提示」小节（注意是「行动」不是「行业」）")
    return problems


# ---------- 主流程 ----------

def valid_urls(raw: dict) -> set:
    urls = set()
    for k in ("intl", "cn"):
        for it in raw.get(k, []):
            if it.get("url"):
                urls.add(it["url"].rstrip("/"))
    for it in raw.get("github_trending", []):
        if it.get("url"):
            urls.add(it["url"].rstrip("/"))
    return urls


def main():
    parser = argparse.ArgumentParser(description="LLM 日报增强（两阶段）")
    parser.add_argument("raw", help="fetch_news.py 输出的原料 JSON")
    parser.add_argument("skeleton", help="generate_report.py 生成的骨架（LLM 不可用时兜底输出）")
    parser.add_argument("--out", required=True, help="最终日报输出路径")
    args = parser.parse_args()

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    skeleton_text = Path(args.skeleton).read_text(encoding="utf-8")
    if not api_key:
        out_path.write_text(skeleton_text, encoding="utf-8")
        print("⚠️ 未设置 LLM_API_KEY，跳过 LLM 增强（输出为骨架版）")
        return 0

    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    now = datetime.now(CN_TZ)
    date_full = f"{now:%Y年%m月%d日}（周{WEEKDAYS[now.weekday()]}）"
    allowed = valid_urls(raw)
    trending = raw.get("github_trending", [])

    # ---- 阶段1：选稿 ----
    print("▶ 阶段 1/2：LLM 选稿")
    sel_resp = call_llm(
        [{"role": "system", "content": SELECT_SYSTEM},
         {"role": "user", "content":
             f"【国外候选 {len(raw.get('intl', []))} 条】\n{fmt_candidates(raw.get('intl', []), 'I')}\n\n"
             f"【国内候选 {len(raw.get('cn', []))} 条】\n{fmt_candidates(raw.get('cn', []), 'C')}"}],
        max_tokens=4096, temperature=0.2, timeout=180)

    intl_idx, cn_idx = [], []
    if sel_resp:
        msg = sel_resp["choices"][0].get("message", {}) or {}
        text = (msg.get("content") or "") + "\n" + (msg.get("reasoning_content") or "")
        intl_idx, cn_idx = parse_selection(text, len(raw.get("intl", [])), len(raw.get("cn", [])))
        if intl_idx or cn_idx:
            print(f"  LLM 选择：国外 {len(intl_idx)} 条 / 国内 {len(cn_idx)} 条")
    if not intl_idx or not cn_idx:
        print("  ⚠️ 选稿解析失败，使用确定性兜底选稿")
        intl_idx = heuristic_select(raw.get("intl", []), 13)
        cn_idx = heuristic_select(raw.get("cn", []), 6)

    sel_intl = [raw["intl"][i] for i in intl_idx] if raw.get("intl") else []
    sel_cn = [raw["cn"][i] for i in cn_idx] if raw.get("cn") else []
    if not sel_intl and not sel_cn:
        out_path.write_text(skeleton_text, encoding="utf-8")
        print("❌ 候选为空，输出骨架版")
        return 1

    # ---- 阶段2：写作（含一次格式问题反馈重写） ----
    print("▶ 阶段 2/2：LLM 写作")
    write_prompt = build_write_prompt(date_full, sel_intl, sel_cn, trending)
    messages = [{"role": "system", "content": WRITE_SYSTEM},
                {"role": "user", "content": write_prompt}]

    text, problems = "", []
    for round_no in (1, 2):
        resp = call_llm(messages, max_tokens=8192, temperature=0.6, timeout=300)
        if not resp:
            break
        text = resp["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("markdown"):
                text = text[len("markdown"):]
        text = text.strip()
        problems = validate_report(text, bool(trending))
        if not problems:
            break
        print(f"  ⚠️ 第 {round_no} 次输出存在 {len(problems)} 个格式问题，反馈重写：")
        for p in problems:
            print(f"    - {p}")
        messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user",
             "content": "你的输出存在以下问题：\n- " + "\n- ".join(problems) +
                        "\n请修正后重新输出完整 Markdown 全文（不是只输出修改点）。",
         }]
        time.sleep(5)

    if not text:
        out_path.write_text(skeleton_text, encoding="utf-8")
        print("❌ LLM 写作失败，降级输出骨架版")
        return 1

    # 链接防幻觉校验
    found = {m.group(2).rstrip("/") for m in re.finditer(r"\[([^\]]*)\]\((https?://[^)]+)\)", text)}
    bad = found - allowed if allowed else set()
    if bad:
        print(f"⚠️ 发现 {len(bad)} 个不在候选清单中的链接（可能是模型幻觉）：")
        for u in list(bad)[:5]:
            print(f"   {u}")

    out_path.write_text(text + "\n", encoding="utf-8")
    if problems:
        print("⚠️ 重写后仍有格式问题，按现状输出")
    print(f"✅ LLM 增强完成 → {out_path}")
    print(f"   国外 {len(sel_intl)} 条 + 国内 {len(sel_cn)} 条 · 趋势 {len(trending)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
