# -*- coding: utf-8 -*-
"""科技新報 — 獨立 fetcher 模組。"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "科技新報"
SOURCE_TYPE = "科技新創"
FEEDS = ['https://technews.tw/feed/']
NOTE = ""


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
