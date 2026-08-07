# -*- coding: utf-8 -*-
"""風傳媒 — 獨立 fetcher 模組。 限制:風傳媒部分內容為會員限定,僅取公開標題與摘要"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "風傳媒"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://www.storm.mg/feeds/all']
NOTE = "風傳媒部分內容為會員限定,僅取公開標題與摘要"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
