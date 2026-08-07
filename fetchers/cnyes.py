# -*- coding: utf-8 -*-
"""Anue鉅亨網 — 獨立 fetcher 模組。 限制:鉅亨 RSS 若失效可改用官網 API,需另行確認使用條款"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "Anue鉅亨網"
SOURCE_TYPE = "財經專業"
FEEDS = ['https://news.cnyes.com/rss/v1/news/category/tw_stock', 'https://news.cnyes.com/rss/v1/news/category/industry']
NOTE = "鉅亨 RSS 若失效可改用官網 API,需另行確認使用條款"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
