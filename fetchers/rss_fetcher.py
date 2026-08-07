# -*- coding: utf-8 -*-
"""通用 RSS/Atom 解析器:各來源模組以自身 feed 清單呼叫 fetch_feeds()。"""
import html
import re
import logging
from datetime import datetime, timezone, timedelta

import feedparser

from fetchers.base import http_get

logger = logging.getLogger("fetcher.rss")
TZ_TAIPEI = timezone(timedelta(hours=8))

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text):
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub("", text)).strip()


def _parse_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc).astimezone(TZ_TAIPEI)
                return dt.isoformat(timespec="seconds")
            except Exception:
                pass
    return None


def fetch_feeds(source_name, source_type, feed_urls):
    """抓取多個 feed,回傳標準化文章 list。單一 feed 失敗僅記錄、不中斷。"""
    items = []
    errors = []
    for url in feed_urls:
        resp = http_get(url)
        if resp is None:
            errors.append(f"feed 無法取得:{url}")
            continue
        parsed = feedparser.parse(resp.content)
        if parsed.bozo and not parsed.entries:
            errors.append(f"feed 解析失敗:{url}")
            continue
        for e in parsed.entries:
            link = e.get("link", "").strip()
            title = _clean(e.get("title", ""))
            if not link or not title:
                continue
            items.append({
                "title": title,
                "summary": _clean(e.get("summary", ""))[:500],
                "source": source_name,
                "source_type": source_type,
                "url": link,
                "published_at": _parse_date(e),
            })
    return items, errors
