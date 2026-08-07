# -*- coding: utf-8 -*-
"""企業官網公告/新聞稿抓取。

各公司官網結構不一,採「登錄制」:在 company_sites.json 登錄
公司名稱 → 新聞稿頁面網址(可含 RSS)。未登錄的公司無法自動抓取官網,
查詢時回報限制並建議人工查閱。
"""
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import http_get
from fetchers.rss_fetcher import fetch_feeds

logger = logging.getLogger("fetcher.company_site")

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "company_sites.json"


def _load_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def fetch_company_news(company_name):
    """回傳 (items, note)。items 為標準化文章 list。"""
    registry = _load_registry()
    entry = registry.get(company_name)
    if not entry:
        return [], (f"「{company_name}」尚未登錄官網新聞稿頁面,無法自動抓取官方公告;"
                    f"請於 company_sites.json 登錄,或人工查閱該公司官網。")

    url = entry.get("url", "")
    if entry.get("type") == "rss":
        items, errors = fetch_feeds(f"{company_name}官網", "企業官網", [url])
        note = ";".join(errors) if errors else ""
        return items, note

    # 一般 HTML 頁面:擷取連結標題(僅公開頁面,遵守 robots.txt)
    resp = http_get(url)
    if resp is None:
        return [], f"官網頁面無法取得:{url}"
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    selector = entry.get("selector", "a")
    for a in soup.select(selector)[:30]:
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not title or len(title) < 8 or not href:
            continue
        items.append({
            "title": title,
            "summary": "",
            "source": f"{company_name}官網",
            "source_type": "企業官網",
            "url": urljoin(url, href),
            "published_at": None,
        })
    note = "" if items else "官網頁面已取得但未擷取到公告連結,請確認 selector 設定。"
    return items, note
