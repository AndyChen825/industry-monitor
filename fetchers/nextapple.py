# -*- coding: utf-8 -*-
"""壹蘋新聞網 — 獨立 fetcher 模組。 官方 API RSS,2026-08 實測可用"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "壹蘋新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://news.nextapple.com/api/rss/category/latest']
NOTE = "官方 API RSS,2026-08 實測可用"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
