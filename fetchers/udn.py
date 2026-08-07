# -*- coding: utf-8 -*-
"""聯合新聞網 — 獨立 fetcher 模組。 限制:RSS 服務回傳空白項目(頻道疑已停用),2026-08 實測確認;財經內容由「經濟日報網」來源涵蓋"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "聯合新聞網"
SOURCE_TYPE = "綜合新聞"
FEEDS = []
NOTE = "RSS 服務回傳空白項目(頻道疑已停用),2026-08 實測確認;財經內容由「經濟日報網」來源涵蓋"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
