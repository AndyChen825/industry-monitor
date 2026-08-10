# -*- coding: utf-8 -*-
"""Yahoo奇摩新聞 — 獨立 fetcher 模組(含原始媒體出處還原)。

Yahoo 為授權轉載平台,RSS 本身不含原始媒體標示。
對「資料庫尚無」的新文章多抓一次文章頁,解析 JSON-LD
(NewsArticle.provider.name)還原原始媒體,來源標為
「<原始媒體>(Yahoo轉載)」;解析失敗則維持 Yahoo奇摩新聞。
藉此間接涵蓋中時、工商、NOWnews、TVBS、三立、今周刊等
無公開 RSS 或禁止直接抓取的合作媒體內容。
"""
import json
import logging

from bs4 import BeautifulSoup

from fetchers.base import http_get
from fetchers.rss_fetcher import fetch_feeds

logger = logging.getLogger("fetcher.yahoo")

NAME = "Yahoo奇摩新聞"
SOURCE_TYPE = "綜合新聞"
FEEDS = [
    "https://tw.news.yahoo.com/rss/finance",
    "https://tw.news.yahoo.com/rss",
]
NOTE = ("Yahoo 為授權聚合平台;新文章會解析文章頁 JSON-LD 還原原始出處,"
        "標為「媒體名(Yahoo轉載)」")
MAX_ENRICH = 120   # 單次執行最多做出處還原的頁面數(控制請求量)


def _provider_name(html):
    """從文章頁 JSON-LD 取出 NewsArticle 的原始媒體名稱。"""
    soup = BeautifulSoup(html, "html.parser")
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (ValueError, TypeError):
            continue
        for o in (data if isinstance(data, list) else [data]):
            if isinstance(o, dict) and o.get("@type") in ("NewsArticle", "Article"):
                prov = o.get("provider") or o.get("publisher") or {}
                if isinstance(prov, dict) and prov.get("name"):
                    return prov["name"].strip()
    return None


def _known_urls(urls):
    """回傳 urls 中已存在於資料庫者(已入庫的文章不再重抓頁面)。"""
    try:
        from db import get_conn
        conn = get_conn()
        known = set()
        chunk_size = 200
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            q = f"SELECT url FROM articles WHERE url IN ({','.join('?' * len(chunk))})"
            known.update(r[0] for r in conn.execute(q, chunk))
        conn.close()
        return known
    except Exception:  # noqa: BLE001 — 還原失敗不影響主要抓取
        return set()


def fetch():
    items, errors = fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
    if not items:
        return items, errors
    known = _known_urls([it["url"] for it in items])
    enriched = restored = 0
    for it in items:
        if it["url"] in known or enriched >= MAX_ENRICH:
            continue
        page = http_get(it["url"])
        enriched += 1
        if page is None:
            continue
        name = _provider_name(page.text)
        if name and "Yahoo" not in name:
            it["source"] = f"{name}(Yahoo轉載)"
            restored += 1
    if enriched:
        logger.info("Yahoo 出處還原:處理 %d 篇新文章,成功還原 %d 篇", enriched, restored)
    return items, errors
