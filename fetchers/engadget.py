# -*- coding: utf-8 -*-
"""Engadget — 獨立 fetcher 模組。 英文媒體,2026-08 實測可用"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "Engadget"
SOURCE_TYPE = "國際科技"
FEEDS = ['https://www.engadget.com/rss.xml']
NOTE = "英文媒體,2026-08 實測可用"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
