# -*- coding: utf-8 -*-
"""今周刊 — 獨立 fetcher 模組。 限制:官網無公開 RSS(/rss 回傳一般網頁),2026-08 實測確認;無法自動抓取"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "今周刊"
SOURCE_TYPE = "深度雜誌"
FEEDS = []
NOTE = "官網無公開 RSS(/rss 回傳一般網頁),2026-08 實測確認;無法自動抓取"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
