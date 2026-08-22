#!/usr/bin/env python3
"""AI 日报信息源抓取模块
多源抓取国内外 AI 资讯，输出结构化 JSON。
设计原则：每源超时 12 秒、失败 1 次即放弃（配合 Agent 联网搜索兜底）。
"""
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from html import unescape

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# 中文 AI 关键词（用于国内源过滤）
CN_AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "大语言模型", "GPT", "ChatGPT", "OpenAI",
    "Claude", "Anthropic", "Gemini", "DeepSeek", "深度求索", "通义", "文心",
    "豆包", "Kimi", "智谱", "GLM", "Llama", "开源模型", "智能体", "Agent",
    "推理模型", "多模态", "AIGC", "生成式", "算力", "英伟达", "NVIDIA",
    "机器学习", "神经网络", "具身智能", "机器人", "自动驾驶", "腾讯", "阿里",
    "百度", "字节", "华为", "昇腾",
]


def _match_cn_ai(title: str) -> bool:
    return any(k in title for k in CN_AI_KEYWORDS)


def _get(url: str, name: str, timeout: int = 12):
    """GET 请求，失败打印并返回 None（单次放弃策略）"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [{name}] 抓取失败（转由 Agent 联网搜索兜底）: {str(e)[:70]}")
        return None


def _get_bytes(url: str, name: str, timeout: int = 12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  [{name}] 抓取失败: {str(e)[:70]}")
        return None


def _parse_rss(content, name: str, limit: int = 10):
    if feedparser is None or content is None:
        return []
    try:
        feed = feedparser.parse(content)
        items = []
        for e in feed.entries[:limit]:
            t = unescape(e.get("title", "")).strip()
            l = e.get("link", "")
            if t and l:
                items.append({"title": t, "url": l, "source": name})
        return items
    except Exception as e:
        print(f"  [{name}] RSS 解析失败: {str(e)[:70]}")
        return []


# ---------- 国外源 ----------

def fetch_techcrunch(limit=12):
    html = _get("https://techcrunch.com/category/artificial-intelligence/", "TechCrunch")
    if not html:
        return []
    pairs = re.findall(
        r'<a[^>]*href="(https://techcrunch\.com/20\d\d/\d\d/\d\d/[^"]+)"[^>]*>([^<]{15,200})</a>',
        html)
    seen, out = set(), []
    for url, t in pairs:
        t = unescape(t.strip())
        if url not in seen and t and not t.startswith("http"):
            seen.add(url)
            out.append({"title": t, "url": url, "source": "TechCrunch"})
    return out[:limit]


def fetch_theverge(limit=10):
    content = _get_bytes(
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "TheVerge")
    return _parse_rss(content, "The Verge", limit)


def fetch_google_ai_blog(limit=10):
    html = _get("https://blog.google/technology/ai/", "GoogleAI")
    if not html:
        return []
    items = re.findall(
        r'href="(https://blog\.google/[^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*([A-Za-z][^<]{15,150})</',
        html)
    seen, out = set(), []
    for url, t in items:
        t = unescape(t.strip())
        if url not in seen and "/technology/ai/" not in url and t:
            seen.add(url)
            out.append({"title": t, "url": url, "source": "Google AI Blog"})
    return out[:limit]


def fetch_hackernews(limit=15):
    """HN Algolia API（主站被墙时的替代通道）"""
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": "AI OR LLM OR OpenAI OR Claude OR GPT OR agent",
                    "tags": "story", "hitsPerPage": 40,
                    "numericFilters": "points>20"},
            headers=HEADERS, timeout=12)
        hits = r.json().get("hits", [])
        out = []
        for h in hits:
            if not h.get("title"):
                continue
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            out.append({"title": h["title"], "url": url, "source": "Hacker News",
                        "meta": f"{h.get('points', 0)} 分 / {h.get('num_comments', 0)} 评论"})
        return out[:limit]
    except Exception as e:
        print(f"  [HackerNews] 抓取失败: {str(e)[:70]}")
        return []


def fetch_arxiv(limit=8):
    try:
        r = requests.get(
            "http://export.arxiv.org/api/query",
            params={"search_query": "cat:cs.AI", "sortBy": "submittedDate",
                    "sortOrder": "descending", "max_results": limit},
            headers=HEADERS, timeout=12)
        if feedparser is None:
            return []
        feed = feedparser.parse(r.content)
        return [{"title": e.get("title", "").replace("\n", " ").strip(),
                 "url": e.get("link", ""), "source": "arXiv"} for e in feed.entries]
    except Exception as e:
        print(f"  [arXiv] 抓取失败: {str(e)[:70]}")
        return []


# ---------- 国内源 ----------

def fetch_qbitai(limit=10):
    content = _get_bytes("https://www.qbitai.com/feed", "量子位")
    return _parse_rss(content, "量子位", limit)


def fetch_ithome(limit=15):
    content = _get_bytes("https://www.ithome.com/rss/", "IT之家")
    items = _parse_rss(content, "IT之家", limit + 10)
    return [i for i in items if _match_cn_ai(i["title"])][:limit]


def fetch_36kr(limit=8):
    content = _get_bytes("https://36kr.com/feed", "36氪")
    items = _parse_rss(content, "36氪", limit + 15)
    return [i for i in items if _match_cn_ai(i["title"])][:limit]


def fetch_zhidx(limit=10):
    html = _get("https://www.zhidx.com/", "智东西")
    if not html:
        return []
    titles = re.findall(
        r'<a[^>]*href="(https://www\.zhidx\.com/p/\d+\.html)"[^>]*>([^<]{10,80})</a>', html)
    seen, out = set(), []
    for url, t in titles:
        t = unescape(t.strip())
        if url not in seen and t:
            seen.add(url)
            out.append({"title": t, "url": url, "source": "智东西"})
    return out[:limit]


def fetch_leiphone(limit=10):
    html = _get("https://www.leiphone.com/", "雷锋网")
    if not html:
        return []
    items = re.findall(
        r'href="(https://www\.leiphone\.com/[^"]+)"[^>]*>\s*([^<]{10,100})\s*</a>', html)
    seen, out = set(), []
    for url, t in items:
        t = unescape(t.strip())
        if url not in seen and t and not url.endswith((".png", ".jpg", ".css")):
            seen.add(url)
            out.append({"title": t, "url": url, "source": "雷锋网"})
    return out[:limit]


def fetch_tmtpost(limit=10):
    html = _get("https://www.tmtpost.com/", "钛媒体")
    if not html:
        return []
    t2 = re.findall(
        r'<a[^>]*href="(https://www\.tmtpost\.com/\d+\.html)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{8,100})',
        html)
    seen, out = set(), []
    for url, t in t2:
        t = unescape(t.strip())
        if url not in seen and t:
            seen.add(url)
            out.append({"title": t, "url": url, "source": "钛媒体"})
    return [i for i in out if _match_cn_ai(i["title"])][:limit]


# ---------- 汇总 ----------

INTL_FETCHERS = {
    "techcrunch": fetch_techcrunch,
    "theverge": fetch_theverge,
    "google": fetch_google_ai_blog,
    "hackernews": fetch_hackernews,
    "arxiv": fetch_arxiv,
}

CN_FETCHERS = {
    "qbitai": fetch_qbitai,
    "ithome": fetch_ithome,
    "36kr": fetch_36kr,
    "zhidx": fetch_zhidx,
    "leiphone": fetch_leiphone,
    "tmtpost": fetch_tmtpost,
}


def fetch_all(enabled_intl=None, enabled_cn=None):
    """抓取所有源。enabled 为 None 时使用默认全部。"""
    enabled_intl = enabled_intl or list(INTL_FETCHERS)
    enabled_cn = enabled_cn or list(CN_FETCHERS)

    intl, cn = [], []
    print("▶ 抓取国外源…")
    for key in enabled_intl:
        if key in INTL_FETCHERS:
            items = INTL_FETCHERS[key]()
            print(f"  {key}: {len(items)} 条")
            intl += items
    print("▶ 抓取国内源…")
    for key in enabled_cn:
        if key in CN_FETCHERS:
            items = CN_FETCHERS[key]()
            print(f"  {key}: {len(items)} 条")
            cn += items

    return {"intl": intl, "cn": cn,
            "stats": {"intl_count": len(intl), "cn_count": len(cn)},
            "fetched_at": datetime.now().isoformat(timespec="seconds")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 日报信息源抓取")
    parser.add_argument("--out", default="raw_material.json", help="输出 JSON 路径")
    parser.add_argument("--intl", help="启用的国外源，逗号分隔（默认全部）")
    parser.add_argument("--cn", help="启用的国内源，逗号分隔（默认全部）")
    args = parser.parse_args()

    data = fetch_all(
        enabled_intl=args.intl.split(",") if args.intl else None,
        enabled_cn=args.cn.split(",") if args.cn else None,
    )
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n共 {data['stats']['intl_count']} 条国外 + {data['stats']['cn_count']} 条国内")
    print(f"已保存 → {args.out}")
