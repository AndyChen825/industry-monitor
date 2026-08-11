# -*- coding: utf-8 -*-
"""靜態網站產生器(GitHub Pages 部署用)。

從 SQLite 匯出資料為 JSON + 產出當週 Word 報告,連同靜態儀表板頁面
輸出至 docs/(GitHub Pages 發布資料夾)。

用法:python static_build.py
"""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import BASE_DIR, INDUSTRIES
from db import get_conn, query_articles, latest_fetch_status
from analysis.keywords import top_keywords
from analysis.companies import build_watchlist, build_stock_quotes_by_abbr

TZ_TAIPEI = timezone(timedelta(hours=8))
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = DOCS_DIR / "data"
REPORTS_DIR = DOCS_DIR / "reports"
TEMPLATE = BASE_DIR / "static_site" / "index.html"
MAX_ARTICLE_DAYS = 400   # 匯出天數上限(涵蓋 YTD)
KEEP_REPORTS = 12        # 保留最近 N 份週報


def build():
    for d in (DATA_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    now = datetime.now(TZ_TAIPEI)
    since = (now - timedelta(days=MAX_ARTICLE_DAYS)).strftime("%Y-%m-%d")
    conn = get_conn()
    articles = query_articles(conn, start_date=since, limit=100000)
    status = latest_fetch_status(conn)

    # 文章資料(僅保留前端需要的欄位)
    slim = [
        {
            "title": a["title"],
            "summary": (a.get("summary") or "")[:200],
            "source": a["source"],
            "url": a["url"],
            "published_at": a.get("published_at") or "",
            "industry": a.get("industry"),
        }
        for a in articles
    ]
    (DATA_DIR / "articles.json").write_text(
        json.dumps(slim, ensure_ascii=False), encoding="utf-8")

    # 各預設期間之關鍵字詞頻(文字雲)
    presets = {
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "90d": now - timedelta(days=90),
        "ytd": now.replace(month=1, day=1, hour=0, minute=0, second=0),
    }
    # 每期間一組全產業詞頻 + 每產業各一組(供產業籤切換文字雲)
    keywords = {}
    for key, start_dt in presets.items():
        start_s = start_dt.strftime("%Y-%m-%d")
        subset = [a for a in articles if (a.get("published_at") or "") >= start_s]
        group = {"all": top_keywords(subset, limit=40)}
        for ind in INDUSTRIES:
            sub_i = [a for a in subset if a.get("industry") == ind]
            if sub_i:
                group[ind] = top_keywords(sub_i, limit=40)
        keywords[key] = group
    (DATA_DIR / "keywords.json").write_text(
        json.dumps(keywords, ensure_ascii=False), encoding="utf-8")

    watchlist = build_watchlist()

    # 當週 Word 報告:僅於週一產出(或設 FORCE_REPORT=1 強制、或尚無任何報告時)
    import os
    existing = list(REPORTS_DIR.glob("*.docx"))
    if now.weekday() == 0 or os.environ.get("FORCE_REPORT") == "1" or not existing:
        from report.word_report import build_report
        start_s = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_s = now.strftime("%Y-%m-%d")
        week_arts = query_articles(conn, start_date=start_s, end_date=end_s, limit=20000)
        report_name = f"台灣產業趨勢監測週報_{start_s}_{end_s}.docx"
        build_report(week_arts, start_s, end_s, fetch_status=status,
                     title="台灣產業趨勢監測週報", out_path=REPORTS_DIR / report_name,
                     watchlist=watchlist)
        print(f"週報已產出:{report_name}")
    else:
        print("非週一,僅更新資料,不產出新週報")
    conn.close()

    # 只保留最近 N 份報告
    all_reports = sorted(REPORTS_DIR.glob("*.docx"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
    for old in all_reports[KEEP_REPORTS:]:
        old.unlink()
    report_files = [p.name for p in all_reports[:KEEP_REPORTS]]

    # meta:產出時間、來源狀態、報告清單
    meta = {
        "generated_at": now.isoformat(timespec="seconds"),
        "article_count": len(slim),
        "fetch_status": status,
        "reports": report_files,
        "watchlist": watchlist,
    }
    # 上市櫃最近收盤價與漲跌幅(附行情所屬日期)
    meta["quotes"], meta["quotes_date"] = build_stock_quotes_by_abbr()
    (DATA_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # 儀表板頁面
    shutil.copyfile(TEMPLATE, DOCS_DIR / "index.html")
    # 停用 Jekyll 處理(檔名含中文與底線時避免被略過)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"靜態網站已產出:{DOCS_DIR}")
    print(f"文章 {len(slim)} 筆;報告 {len(report_files)} 份;產出時間 {meta['generated_at']}")


if __name__ == "__main__":
    build()
