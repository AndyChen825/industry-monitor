# -*- coding: utf-8 -*-
"""PTT 論壇 — 獨立 fetcher 模組(筆電相關看板)。

PTT 無 robots.txt 限制(2026-08 實測),以看板 index 頁擷取文章標題,
每板每次抓最近數頁(遵守 2 秒間隔)。
其他主要論壇(Mobile01/Dcard/巴哈姆特/Reddit)robots.txt 均禁止爬取,
依規範不抓取。
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import http_get

logger = logging.getLogger("fetcher.ptt")

NAME = "PTT"
SOURCE_TYPE = "論壇"
TZ_TAIPEI = timezone(timedelta(hours=8))

# (看板, 顯示來源名稱)
BOARDS = [
    ("nb-shopping", "PTT 筆電板(nb-shopping)"),
    ("PC_Shopping", "PTT 電蝦板(PC_Shopping)"),
]
PAGES_PER_BOARD = 3   # 每次抓最近 N 頁(每頁約 20 篇)
NOTE = ("PTT 看板標題(無全文);Mobile01/Dcard/巴哈姆特/Reddit 之 robots.txt "
        "禁止爬取,依規範不納入")

BASE = "https://www.ptt.cc"


def _parse_date(mmdd, now):
    """PTT 列表日期為 M/DD(無年份);月份大於當前月即視為去年。"""
    try:
        m, d = (int(x) for x in mmdd.strip().split("/"))
        year = now.year - 1 if m > now.month else now.year
        return datetime(year, m, d, tzinfo=TZ_TAIPEI).isoformat(timespec="seconds")
    except (ValueError, AttributeError):
        return None


def _fetch_board(board, source_name, now):
    items, errors = [], []
    index_url = f"{BASE}/bbs/{board}/index.html"
    url = index_url
    for _page in range(PAGES_PER_BOARD):
        resp = http_get(url)
        if resp is None:
            errors.append(f"{source_name} 頁面無法取得:{url}")
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        for ent in soup.select("div.r-ent"):
            a = ent.select_one("div.title a")
            if a is None:      # 已刪除文章
                continue
            title = a.get_text(strip=True)
            if title.startswith("[公告]") or title.startswith("(本文已被刪除)"):
                continue
            date_el = ent.select_one("div.date")
            items.append({
                "title": title,
                "summary": "",
                "source": source_name,
                "source_type": SOURCE_TYPE,
                "url": urljoin(BASE, a["href"]),
                "published_at": _parse_date(date_el.get_text() if date_el else "", now),
            })
        prev = soup.find("a", string=re.compile("上頁"))
        if not prev or not prev.get("href"):
            break
        url = urljoin(BASE, prev["href"])
    return items, errors


def fetch():
    """回傳 (items, errors)。單一看板失敗不影響其他看板。"""
    now = datetime.now(TZ_TAIPEI)
    items, errors = [], []
    for board, source_name in BOARDS:
        try:
            b_items, b_errors = _fetch_board(board, source_name, now)
            items.extend(b_items)
            errors.extend(b_errors)
        except Exception as e:  # noqa: BLE001 — 單板錯誤不可中斷整體
            errors.append(f"{source_name}:{e}")
    return items, errors
