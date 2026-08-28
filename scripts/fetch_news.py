#!/usr/bin/env python3
"""AI 日报信息源抓取模块
多源抓取国内外 AI 资讯 + GitHub Trending 周榜 + Google News 检索补充，
并为候选条目并发抓取正文摘要，输出结构化 JSON。

设计原则：
- 直抓源单次失败即放弃（每源超时 12s），缺口由 Google News 检索源补位；
- GitHub Trending 周榜直抓 github.com/trending?since=weekly（Actions 出口可达）；
- 候选正文用线程池并发抓取，让 LLM 基于真实内容写摘要，而非只看标题。
"""
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
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

# GitHub Trending AI 过滤关键词（宽松匹配，保证趋势表不空）
GH_AI_KEYWORDS = [
    "ai", "llm", "gpt", "agent", "rag", "model", "ml", "transformer",
    "diffusion", "whisper", "chatbot", "prompt", "neural", "vision",
    "speech", "voice", "inference", "training", "copilot", "mcp",
    "人工智能", "大模型", "智能",
]

# Google News 检索补充查询（when:2d 限定近两天）
GNEWS_INTL_QUERIES = [
    ("AI funding OR investment", 8),
    ('AI regulation OR "AI Act" OR AI policy', 8),
]
GNEWS_CN_QUERIES = [
    ("人工智能 融资", 8),
    ("AI 监管 OR 大模型 政策", 8),
]

# 这些域名的页面不值得抓正文（聚合页/讨论页/已有摘要）
NO_FETCH_HOSTS = ("news.ycombinator.com", "news.google.com")


def _match_cn_ai(title: str) -> bool:
    return any(k in title for k in CN_AI_KEYWORDS)


def _match_gh_ai(item: dict) -> bool:
    text = f"{item.get('title','')} {item.get('desc','')}".lower()
    return any(k in text for k in GH_AI_KEYWORDS)


def _get(url: str, name: str, timeout: int = 12):
    """GET 请求，失败打印并返回 None（单次放弃策略）"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [{name}] 抓取失败（由检索源补位）: {str(e)[:70]}")
        return None


def _get_bytes(url: str, name: str, timeout: int = 12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  [{name}] 抓取失败: {str(e)[:70]}")
        return None


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rss(content, name: str, limit: int = 10, keep_summary: bool = True):
    if feedparser is None or content is None:
        return []
    try:
        feed = feedparser.parse(content)
        items = []
        for e in feed.entries[:limit]:
            t = unescape(e.get("title", "")).strip()
            l = e.get("link", "")
            if not (t and l):
                continue
            item = {"title": t, "url": l, "source": name}
            if keep_summary:
                summary = _strip_tags(e.get("summary", ""))[:400]
                if summary:
                    item["summary"] = summary
            items.append(item)
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
    """HN Algolia API（主站被墙时的替代通道），只取近 48 小时且 >20 分"""
    try:
        import time as _time
        since = int(_time.time()) - 48 * 3600
        r = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": "AI OR LLM OR OpenAI OR Claude OR GPT OR agent",
                    "tags": "story", "hitsPerPage": 40,
                    "numericFilters": f"points>20,created_at_i>{since}"},
            headers=HEADERS, timeout=12)
        hits = r.json().get("hits", [])
        out = []
        for h in hits:
            if not h.get("title"):
                continue
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            out.append({"title": h["title"], "url": url, "source": "Hacker News",
                        "meta": f"HN {h.get('points', 0)} 分 / {h.get('num_comments', 0)} 评论"})
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
        out = []
        for e in feed.entries:
            summary = _strip_tags(e.get("summary", ""))[:400]
            out.append({"title": e.get("title", "").replace("\n", " ").strip(),
                        "url": e.get("link", ""), "source": "arXiv",
                        "summary": summary})
        return out
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


# ---------- GitHub Trending 周榜 ----------

def fetch_github_trending(max_items=8):
    """抓 github.com/trending?since=weekly，解析周增 Star，AI 关键词过滤。
    Actions 出口直连可达；本机网络不通时优雅返回空列表。"""
    items, seen = [], set()
    for lang in ("", "python", "typescript", "rust", "go"):
        url = "https://github.com/trending" + (f"/{lang}" if lang else "") + "?since=weekly"
        html = _get(url, f"GH-Trending({lang or 'all'})", timeout=15)
        if not html:
            continue
        for block in re.split(r'<article class="Box-row">', html)[1:]:
            m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', block)
            if not m:
                continue
            path = m.group(1).strip("/")
            if path in seen or path.count("/") != 1:
                continue
            seen.add(path)
            stars = re.search(r"([\d,]+)\s+stars\s+(this week|this month|today)", block)
            desc_m = re.search(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', block, re.S)
            desc = _strip_tags(desc_m.group(1))[:120] if desc_m else ""
            meta = f"周增 {stars.group(1)} Star" if stars else ""
            items.append({"title": path, "url": f"https://github.com/{path}",
                          "source": "GitHub Trending", "desc": desc, "meta": meta})
        if len(items) >= max_items * 3:
            break
    ai_items = [i for i in items if _match_gh_ai(i)]
    if len(ai_items) < 3:  # AI 过滤太严时放宽，保证趋势表不空
        ai_items = items
    return ai_items[:max_items]


# ---------- Google News 检索补充 ----------

def fetch_google_news(query: str, lang: str = "en", limit: int = 8):
    """Google News RSS 检索。作为直抓失败维度的补位（政策/资本/官方动态等）。
    标题保留 outlet 名；链接为 news.google 跳转链，不再抓正文。"""
    if feedparser is None:
        return []
    if lang == "zh":
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    else:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    content = _get_bytes(url, f"GNews({query[:24]})")
    if not content:
        return []
    try:
        feed = feedparser.parse(content)
        out = []
        for e in feed.entries[:limit]:
            t = unescape(e.get("title", "")).strip()
            outlet = ""
            src = e.get("source")
            if isinstance(src, dict):
                outlet = (src.get("title") or "").strip()
            if outlet and t.endswith(f" - {outlet}"):
                t = t[: -len(outlet) - 3].strip()
            if not t:
                continue
            out.append({"title": t, "url": e.get("link", ""),
                        "source": outlet or "Google News",
                        "via": "search", "no_fetch": True})
        return out
    except Exception as e:
        print(f"  [GNews] 解析失败: {str(e)[:70]}")
        return []


# ---------- 正文抓取（并发） ----------

def _extract_text(html: str, limit: int = 1500) -> str:
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    # 优先取正文容器（WordPress entry-content 等），避免页头导航混入
    container = re.search(
        r'class="[^"]*(?:entry-content|article-content|post-content|articleBody)[^"]*"[^>]*>(.*?)(?:</article>|</main>)',
        html, re.S | re.I)
    scope = container.group(1) if container else html
    paras = re.findall(r"<p[^>]*>(.*?)</p>", scope, flags=re.S | re.I)
    if not container:
        # 无正文容器时丢弃链接密集的段落（导航/页脚）
        paras = [p for p in paras if len(re.findall(r"<a\s", p)) <= 4]
    text = " ".join(paras) if paras else scope
    return _strip_tags(text)[:limit]


def _fetch_article_text(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return _extract_text(r.text)
    except Exception:
        return ""


def _needs_fetch(item: dict) -> bool:
    if item.get("summary") or item.get("no_fetch"):
        return False
    host = re.sub(r"^https?://([^/]+).*$", r"\1", item.get("url", "")).lower()
    return bool(host) and not any(h in host for h in NO_FETCH_HOSTS)


def enrich_contents(data: dict, max_workers: int = 12, max_pages: int = 60):
    """为缺摘要的候选并发抓正文（前 1500 字），失败置空串（LLM 端降级用标题写）。"""
    targets = [it for region in ("intl", "cn") for it in data.get(region, [])
               if _needs_fetch(it)][:max_pages]
    if not targets:
        return 0
    print(f"▶ 并发抓取正文（{len(targets)} 篇, {max_workers} 线程）…")
    ok = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_article_text, it["url"]): it for it in targets}
        for fu in as_completed(futures):
            text = fu.result()
            if text:
                futures[fu]["content"] = text
                ok += 1
    print(f"  正文抓取成功 {ok}/{len(targets)} 篇")
    return ok


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
    "zhidx": fetch_zhidx,
    "leiphone": fetch_leiphone,
    "tmtpost": fetch_tmtpost,
}


def _dedup(items: list) -> list:
    seen, out = set(), []
    for it in items:
        key = it.get("url", "").rstrip("/")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def fetch_all(enabled_intl=None, enabled_cn=None, skip_search=False,
              skip_trending=False, skip_content=False):
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

    direct_intl, direct_cn = len(intl), len(cn)

    if not skip_search:
        print("▶ 检索补充（Google News）…")
        search_intl = []
        for q, n in GNEWS_INTL_QUERIES:
            search_intl += fetch_google_news(q, "en", n)
        search_cn = []
        for q, n in GNEWS_CN_QUERIES:
            search_cn += fetch_google_news(q, "zh", n)
        print(f"  检索补充: 国外 {len(search_intl)} 条 / 国内 {len(search_cn)} 条")
        intl += search_intl
        cn += search_cn

    intl, cn = _dedup(intl), _dedup(cn)

    trending = [] if skip_trending else fetch_github_trending()
    print(f"▶ GitHub Trending 周榜: {len(trending)} 个项目")

    if not skip_content:
        enrich_contents({"intl": intl, "cn": cn})

    with_content = sum(1 for it in intl + cn if it.get("content") or it.get("summary"))
    return {"intl": intl, "cn": cn, "github_trending": trending,
            "stats": {"intl_count": len(intl), "cn_count": len(cn),
                      "direct_intl": direct_intl, "direct_cn": direct_cn,
                      "content_count": with_content,
                      "trending_count": len(trending)},
            "fetched_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 日报信息源抓取")
    parser.add_argument("--out", default="raw_material.json", help="输出 JSON 路径")
    parser.add_argument("--intl", help="启用的国外源，逗号分隔（默认全部）")
    parser.add_argument("--cn", help="启用的国内源，逗号分隔（默认全部）")
    parser.add_argument("--no-search", action="store_true", help="跳过 Google News 检索补充")
    parser.add_argument("--no-trending", action="store_true", help="跳过 GitHub Trending")
    parser.add_argument("--no-content", action="store_true", help="跳过正文抓取（快速测试）")
    args = parser.parse_args()

    data = fetch_all(
        enabled_intl=args.intl.split(",") if args.intl else None,
        enabled_cn=args.cn.split(",") if args.cn else None,
        skip_search=args.no_search,
        skip_trending=args.no_trending,
        skip_content=args.no_content,
    )
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    s = data["stats"]
    print(f"\n共 {s['intl_count']} 条国外 + {s['cn_count']} 条国内"
          f"（直抓 {s['direct_intl']}/{s['direct_cn']}，检索补位其余）")
    print(f"带摘要/正文候选 {s['content_count']} 条 · Trending {s['trending_count']} 个")
    print(f"已保存 → {args.out}")
