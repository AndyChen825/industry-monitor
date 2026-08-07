# -*- coding: utf-8 -*-
"""企業官網公告/新聞稿抓取。

各公司官網結構不一,採「登錄制」:在 company_sites.json 登錄
公司名稱 → 新聞稿頁面設定。支援兩種模式:
- type=rss:標準 RSS
- type=html:一般頁面。以 link_pattern 比對新聞連結,向上尋找卡片
  文字取得標題;可選 date_regex/date_format 解析發布日期、
  strip_texts 移除雜訊字樣。
未登錄的公司無法自動抓取官網,查詢時回報限制並建議人工查閱。
"""
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import http_get
from fetchers.rss_fetcher import fetch_feeds

logger = logging.getLogger("fetcher.company_site")

TZ_TAIPEI = timezone(timedelta(hours=8))
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "company_sites.json"


def load_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _extract_card(anchor, strip_texts):
    """由連結向上找含標題的卡片文字(最多 3 層)。"""
    node = anchor
    for _ in range(3):
        node = node.parent
        if node is None:
            return ""
        text = node.get_text(" ", strip=True)
        for s in strip_texts:
            text = text.replace(s, "")
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 12:
            return text
    return ""


def fetch_company_news(company_name):
    """回傳 (items, note)。items 為標準化文章 list。"""
    registry = load_registry()
    entry = registry.get(company_name)
    if not entry:
        return [], (f"「{company_name}」尚未登錄官網新聞稿頁面,無法自動抓取官方公告;"
                    f"請於 company_sites.json 登錄,或人工查閱該公司官網。")
    if entry.get("disabled"):
        return [], f"{company_name}官網:{entry.get('note', '已停用')}"

    url = entry.get("url", "")
    if entry.get("type") == "rss":
        items, errors = fetch_feeds(f"{company_name}官網", "企業官網", [url])
        return items, (";".join(errors) if errors else "")

    resp = http_get(url)
    if resp is None:
        return [], f"官網頁面無法取得:{url}"
    soup = BeautifulSoup(resp.text, "html.parser")

    link_pattern = entry.get("link_pattern")
    strip_texts = entry.get("strip_texts", [])
    date_regex = entry.get("date_regex")
    date_format = entry.get("date_format")

    if link_pattern:
        anchors = [a for a in soup.find_all("a", href=True)
                   if link_pattern in a["href"]]
    else:
        anchors = soup.select(entry.get("selector", "a"))

    items, seen = [], set()
    for a in anchors[:40]:
        href = urljoin(url, a.get("href", ""))
        if not href or href in seen:
            continue
        seen.add(href)
        if link_pattern:
            text = _extract_card(a, strip_texts)
        else:
            text = a.get_text(strip=True)
        if not text or len(text) < 8:
            continue

        published = None
        if date_regex:
            m = re.search(date_regex, text)
            if m:
                try:
                    dt = datetime.strptime(m.group(1), date_format)
                    published = dt.replace(tzinfo=TZ_TAIPEI).isoformat(timespec="seconds")
                except ValueError:
                    pass
                text = text.replace(m.group(1), "").strip()

        items.append({
            "title": text[:120],
            "summary": "",
            "source": f"{company_name}官網",
            "source_type": "企業官網",
            "url": href,
            "published_at": published,
        })
    note = "" if items else "官網頁面已取得但未擷取到公告,請確認 link_pattern/selector 設定。"
    return items, note
