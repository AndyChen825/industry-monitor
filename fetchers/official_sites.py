# -*- coding: utf-8 -*-
"""企業官網(彙整)— 獨立 fetcher 模組。

逐一抓取 company_sites.json 登錄的公司官網新聞稿。
官網公告若無法解析出發布日期,以抓取當下時間記錄(收錄日期),
確保於期間篩選中可見。
"""
from datetime import datetime, timezone, timedelta

from fetchers.company_site import load_registry, fetch_company_news

NAME = "企業官網"
SOURCE_TYPE = "企業官網"
TZ_TAIPEI = timezone(timedelta(hours=8))


def fetch():
    """回傳 (items, errors)。單一公司失敗不影響其他公司。"""
    items, errors = [], []
    registry = load_registry()
    if not registry:
        return [], ["company_sites.json 尚未登錄任何公司官網"]
    now_iso = datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")
    for company in registry:
        try:
            c_items, note = fetch_company_news(company)
            for it in c_items:
                if not it.get("published_at"):
                    it["published_at"] = now_iso
            items.extend(c_items)
            if note:
                errors.append(note)
        except Exception as e:  # noqa: BLE001 — 單一公司錯誤不可中斷整體
            errors.append(f"{company}官網:{e}")
    return items, errors
