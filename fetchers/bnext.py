# -*- coding: utf-8 -*-
"""數位時代 — 獨立 fetcher 模組。 限制:官網無公開 RSS(常見路徑均 404),2026-08 實測確認;無法自動抓取"""
from fetchers.rss_fetcher import fetch_feeds

NAME = "數位時代"
SOURCE_TYPE = "科技新創"
FEEDS = []
NOTE = "官網無公開 RSS(常見路徑均 404),2026-08 實測確認;無法自動抓取"


def fetch():
    """回傳 (items, errors)。無可用 feed 時回傳空清單並註明限制。"""
    if not FEEDS:
        return [], [NOTE or "此來源無可自動抓取之管道"]
    return fetch_feeds(NAME, SOURCE_TYPE, FEEDS)
