# -*- coding: utf-8 -*-
"""標案商機雷達(政府電子採購網)。

嘗試 g0v 社群開放 API 取得招標公告(2026-08 實測該 API 改版後暫不回傳
JSON,保留嘗試以待恢復);失敗時回傳空清單,前端改提供各關鍵字之
人工快速查詢連結。官方採購網查詢含驗證機制,依規範不做網頁自動化。
"""
import logging

from fetchers.base import http_get

logger = logging.getLogger("fetcher.tenders")

API = "https://pcc.g0v.ronny.tw/api/searchbytitle?query={kw}&page=1"
MANUAL_URL = "https://web.pcc.gov.tw/pis/"
SOURCE_NOTE = "資料來源:政府電子採購網(經 g0v 社群開放 API)"


def fetch_tenders(keywords, per_kw=10):
    """回傳 (records, note)。records: [{date, unit, title, url, keyword}]。"""
    records = []
    api_ok = False
    for kw in keywords:
        resp = http_get(API.format(kw=kw), check_robots=False)
        if resp is None:
            continue
        body = resp.text.strip()
        if not body.startswith("{"):
            continue  # API 目前回傳 HTML(改版中),略過
        try:
            data = resp.json()
        except ValueError:
            continue
        api_ok = True
        for rec in (data.get("records") or [])[:per_kw]:
            brief = rec.get("brief") or {}
            records.append({
                "date": str(rec.get("date", "")),
                "unit": rec.get("unit_name", ""),
                "title": brief.get("title", ""),
                "url": f"https://pcc.g0v.ronny.tw/tender/{rec.get('unit_id', '')}"
                       f"/{rec.get('job_number', '')}",
                "keyword": kw,
            })
    if api_ok:
        note = SOURCE_NOTE
    else:
        note = ("標案開放 API 目前無法取得資料(g0v 端點改版中);"
                "請以下列關鍵字至政府電子採購網人工查詢:" + MANUAL_URL)
    return records, note
