# -*- coding: utf-8 -*-
"""壹蘋新聞網 — 獨立 fetcher 模組。 限制:壹蘋 RSS 若失效需至官網確認"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "壹蘋新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://tw.nextapple.com/rss/latest']
NOTE = "壹蘋 RSS 若失效需至官網確認"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
