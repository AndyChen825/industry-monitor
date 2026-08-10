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

from config import BASE_DIR, COMPANY_WATCHLIST
from db import get_conn, query_articles, latest_fetch_status
from analysis.keywords import top_keywords
from fetchers.base import http_get

# 證交所/櫃買中心 產業別代碼 → 本系統 11 大產業
TWSE_INDUSTRY_MAP = {
    "24": "高科技製造業", "25": "高科技製造業", "26": "高科技製造業",
    "28": "高科技製造業", "31": "高科技製造業",
    "01": "傳統製造業", "02": "傳統製造業", "03": "傳統製造業",
    "04": "傳統製造業", "05": "傳統製造業", "06": "傳統製造業",
    "08": "傳統製造業", "09": "傳統製造業", "10": "傳統製造業",
    "11": "傳統製造業", "12": "傳統製造業", "21": "傳統製造業", "33": "傳統製造業",
    "18": "批發零售業", "29": "批發零售業", "34": "批發零售業", "38": "批發零售業",
    "16": "住宿及餐飲業",
    "27": "資通訊業", "30": "資通訊業", "36": "資通訊業",
    "17": "金融業",
    "22": "醫療保健業",
    "14": "服務業", "15": "服務業", "23": "服務業", "32": "服務業",
    "35": "服務業", "37": "服務業", "20": "服務業",
}

LISTED_CACHE = BASE_DIR / "data" / "listed_companies.json"

# 與日常用語同形的公司簡稱,自動比對必然大量誤計,排除之
# (如需追蹤這些公司,請於 config.COMPANY_WATCHLIST 以全名/別名手動登錄)
AMBIGUOUS_ABBRS = {
    "全台", "全新", "全國", "大眾", "中央", "國際", "亞洲", "第一", "中華",
    "台灣", "環球", "東方", "精英", "時代", "百達", "現代", "自然美",
    "大學", "光明", "南方", "太平洋", "文化", "健康", "數字", "商店",
}

COMPANY_LIST_APIS = [
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",   # 上市
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",  # 上櫃
]


def fetch_listed_companies():
    """取得全體上市櫃公司(簡稱+產業別);失敗時退回快取。"""
    rows = []
    for url in COMPANY_LIST_APIS:
        resp = http_get(url, check_robots=False)  # 官方開放 API
        if resp is None:
            continue
        try:
            rows.extend(resp.json())
        except ValueError:
            continue
    if rows:
        LISTED_CACHE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return rows
    if LISTED_CACHE.exists():
        print("公司名錄 API 失敗,使用上次快取")
        return json.loads(LISTED_CACHE.read_text(encoding="utf-8"))
    return []


def build_watchlist():
    """上市櫃公司名錄(自動)+ 手動觀察清單(補非上市櫃品牌與英文別名)。"""
    watchlist = {}
    for row in fetch_listed_companies():
        abbr = str(row.get("公司簡稱", "")).strip()
        code = str(row.get("產業別", "")).strip().zfill(2)
        industry = TWSE_INDUSTRY_MAP.get(code)
        if not industry or len(abbr) < 2 or abbr in AMBIGUOUS_ABBRS:
            continue
        watchlist.setdefault(industry, {})[abbr] = [abbr]
    # 手動清單合併:同名者聯集別名(補英文名),不同名者新增
    for industry, companies in COMPANY_WATCHLIST.items():
        bucket = watchlist.setdefault(industry, {})
        for name, aliases in companies.items():
            bucket[name] = sorted(set(bucket.get(name, [])) | set(aliases))
    return watchlist

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
    keywords = {}
    for key, start_dt in presets.items():
        start_s = start_dt.strftime("%Y-%m-%d")
        subset = [a for a in articles if (a.get("published_at") or "") >= start_s]
        keywords[key] = top_keywords(subset, limit=40)
    (DATA_DIR / "keywords.json").write_text(
        json.dumps(keywords, ensure_ascii=False), encoding="utf-8")

    # 當週 Word 報告:僅於週一產出(或設 FORCE_REPORT=1 強制、或尚無任何報告時)
    import os
    existing = list(REPORTS_DIR.glob("*.docx"))
    if now.weekday() == 0 or os.environ.get("FORCE_REPORT") == "1" or not existing:
        from report.word_report import build_report
        start_s = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_s = now.strftime("%Y-%m-%d")
        week_arts = query_articles(conn, start_date=start_s, end_date=end_s, limit=2000)
        report_name = f"台灣產業趨勢監測週報_{start_s}_{end_s}.docx"
        build_report(week_arts, start_s, end_s, fetch_status=status,
                     title="台灣產業趨勢監測週報", out_path=REPORTS_DIR / report_name)
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
        "watchlist": build_watchlist(),
    }
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
