# -*- coding: utf-8 -*-
"""中央社 — 獨立 fetcher 模組。"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "中央社"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://feeds.feedburner.com/rsscna/finance', 'https://feeds.feedburner.com/rsscna/technology', 'https://feeds.feedburner.com/rsscna/lifehealth', 'https://feeds.feedburner.com/rsscna/politics']
NOTE = ""


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
