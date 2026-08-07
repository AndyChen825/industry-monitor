# -*- coding: utf-8 -*-
"""三立新聞網 — 獨立 fetcher 模組。 限制:三立無官方完整 RSS,僅財經頻道;失效時僅提供官網連結"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "三立新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = ['https://www.setn.com/rss.aspx?PageGroupID=2']
NOTE = "三立無官方完整 RSS,僅財經頻道;失效時僅提供官網連結"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
