# -*- coding: utf-8 -*-
"""LINE Today — 獨立 fetcher 模組。 限制:LINE Today 無公開 RSS 且 robots.txt 限制爬取;無法自動抓取,僅提供入口 https://today.line.me/tw"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "LINE Today"
SOURCE_TYPE = "綜合新聞"
FEEDS = []
NOTE = "LINE Today 無公開 RSS 且 robots.txt 限制爬取;無法自動抓取,僅提供入口 https://today.line.me/tw"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
