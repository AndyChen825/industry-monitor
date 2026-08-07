# -*- coding: utf-8 -*-
"""中時新聞網 — 獨立 fetcher 模組。 限制:網站 robots.txt 不允許程式抓取,依規範不抓取"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "中時新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = []
NOTE = "網站 robots.txt 不允許程式抓取,依規範不抓取"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
