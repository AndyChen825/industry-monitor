# -*- coding: utf-8 -*-
"""MoneyDJ理財網 — 獨立 fetcher 模組。 限制:網站 TLS 憑證鏈缺少 Subject Key Identifier,Python 預設驗證失敗;暫無法自動抓取"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "MoneyDJ理財網"
SOURCE_TYPE = "財經專業"
FEEDS = []
NOTE = "網站 TLS 憑證鏈缺少 Subject Key Identifier,Python 預設驗證失敗;暫無法自動抓取"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
