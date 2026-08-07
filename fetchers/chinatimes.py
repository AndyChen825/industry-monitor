# -*- coding: utf-8 -*-
"""中時新聞網 — 獨立 fetcher 模組。 限制:中時 RSS 若失效需至官網確認新網址"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "中時新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://www.chinatimes.com/rss/realtimenews-money.xml', 'https://www.chinatimes.com/rss/realtimenews-technologynews.xml']
NOTE = "中時 RSS 若失效需至官網確認新網址"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
