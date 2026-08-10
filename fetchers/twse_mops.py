# -*- coding: utf-8 -*-
"""證交所重大訊息(上市公司)— 獨立 fetcher 模組。

資料來源:證交所 OpenAPI(官方開放資料,供程式介接)
t187ap04_L「上市公司每日重大訊息」。此為法定資訊揭露管道,
可取得台積電、華碩等所有上市公司之官方公告,較新聞稿更權威。
單筆訊息無獨立網址,連結為公開資訊觀測站入口,
以 #公司代號-日期-時間 識別(兼作資料庫去重鍵)。
"""
import logging
import re

from fetchers.base import http_get

logger = logging.getLogger("fetcher.twse")

NAME = "證交所重大訊息"
SOURCE_TYPE = "官方公告"
API = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
MOPS_URL = "https://mops.twse.com.tw/mops/web/t05sr01_1"
NOTE = "上市公司每日重大訊息(證交所 OpenAPI);原文請至公開資訊觀測站以公司代號查詢"


def _roc_to_iso(date_s, time_s):
    """民國日期(如 1150810)+ 時間(如 093000)轉 ISO 8601。"""
    try:
        d = str(date_s).strip()
        t = str(time_s).strip().zfill(6)
        year = int(d[:-4]) + 1911
        month, day = int(d[-4:-2]), int(d[-2:])
        return f"{year:04d}-{month:02d}-{day:02d}T{t[:2]}:{t[2:4]}:{t[4:6]}+08:00"
    except (ValueError, IndexError):
        return None


def fetch():
    """回傳 (items, errors)。"""
    resp = http_get(API, check_robots=False)  # 官方開放 API,設計供程式使用
    if resp is None:
        return [], ["證交所 OpenAPI 無法取得"]
    try:
        data = resp.json()
    except ValueError:
        return [], ["證交所 OpenAPI 回應非 JSON"]

    items = []
    for row in data:
        code = str(row.get("公司代號", "")).strip()
        name = str(row.get("公司名稱", "")).strip()
        subject = re.sub(r"\s+", " ", str(row.get("主旨 ") or row.get("主旨") or "")).strip()
        if not code or not subject:
            continue
        date_s = str(row.get("發言日期", "")).strip()
        time_s = str(row.get("發言時間", "")).strip()
        items.append({
            "title": f"{name}({code}):{subject}"[:200],
            "summary": (f"符合條款:{str(row.get('符合條款', '')).strip()};"
                        f"事實發生日:{str(row.get('事實發生日', '')).strip()}"),
            "source": NAME,
            "source_type": SOURCE_TYPE,
            "url": f"{MOPS_URL}#{code}-{date_s}-{time_s}",
            "published_at": _roc_to_iso(date_s, time_s),
        })
    return items, []
