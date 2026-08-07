# -*- coding: utf-8 -*-
"""Yahoo奇摩新聞 — 獨立 fetcher 模組。 Yahoo 為聚合媒體,原始出處以文章內標示為準"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "Yahoo奇摩新聞"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://tw.news.yahoo.com/rss/finance', 'https://tw.news.yahoo.com/rss']
NOTE = "Yahoo 為聚合媒體,原始出處以文章內標示為準"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
