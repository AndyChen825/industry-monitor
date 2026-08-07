# -*- coding: utf-8 -*-
"""TVBS — 獨立 fetcher 模組。 限制:RSS 路徑已移除(rss/money、rss/tech 均 404),無公開 RSS;無法自動抓取"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "TVBS"
SOURCE_TYPE = "綜合新聞"
FEEDS = []
NOTE = "RSS 路徑已移除(rss/money、rss/tech 均 404),無公開 RSS;無法自動抓取"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
