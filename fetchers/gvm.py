# -*- coding: utf-8 -*-
"""遠見雜誌 — 獨立 fetcher 模組。 限制:遠見 RSS 若失效需至官網確認"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "遠見雜誌"
SOURCE_TYPE = "深度雜誌"
FEEDS = ['https://www.gvm.com.tw/rss']
NOTE = "遠見 RSS 若失效需至官網確認"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
