# -*- coding: utf-8 -*-
"""聯合新聞網 — 獨立 fetcher 模組。 限制:UDN RSS 分類頻道,若失效需至 https://udn.com/rssfeed/ 更新網址"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "聯合新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://udn.com/rssfeed/news/2/6644?ch=news', 'https://udn.com/rssfeed/news/2/6638?ch=news', 'https://udn.com/rssfeed/news/2/7226?ch=news']
NOTE = "UDN RSS 分類頻道,若失效需至 https://udn.com/rssfeed/ 更新網址"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
