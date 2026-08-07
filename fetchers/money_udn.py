# -*- coding: utf-8 -*-
"""經濟日報網 — 獨立 fetcher 模組。 限制:經濟日報部分內容為訂閱制,僅取公開標題與摘要"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "經濟日報網"
SOURCE_TYPE = "財經專業"
FEEDS = ['https://money.udn.com/rssfeed/news/1001/5591?ch=money', 'https://money.udn.com/rssfeed/news/1001/5612?ch=money']
NOTE = "經濟日報部分內容為訂閱制,僅取公開標題與摘要"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
