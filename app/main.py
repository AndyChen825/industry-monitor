# -*- coding: utf-8 -*-
"""網頁介面(FastAPI):期間選擇、公司搜尋、產業瀏覽、Word 報告匯出。"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from config import INDUSTRIES
from db import get_conn, query_articles, latest_fetch_status
from fetchers.findbiz import query_company
from fetchers.company_site import fetch_company_news

TZ_TAIPEI = timezone(timedelta(hours=8))
app = FastAPI(title="台灣產業趨勢監測與公司情報系統")

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"


def resolve_period(period, start, end):
    """期間代碼轉為 (start, end) 日期字串。"""
    now = datetime.now(TZ_TAIPEI)
    end_s = now.strftime("%Y-%m-%d")
    if period == "ytd":
        return f"{now.year}-01-01", end_s
    if period in ("7d", "30d", "90d"):
        days = int(period[:-1])
        return (now - timedelta(days=days)).strftime("%Y-%m-%d"), end_s
    if period == "custom" and start and end:
        return start, end
    return (now - timedelta(days=7)).strftime("%Y-%m-%d"), end_s


@app.get("/", response_class=HTMLResponse)
def index():
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@app.get("/api/industries")
def api_industries(period: str = "7d", start: str = "", end: str = "",
                   industry: str = ""):
    s, e = resolve_period(period, start, end)
    conn = get_conn()
    arts = query_articles(conn, start_date=s, end_date=e,
                          industry=industry or None, limit=1000)
    conn.close()
    counts = {}
    for a in arts:
        if a.get("industry"):
            counts[a["industry"]] = counts.get(a["industry"], 0) + 1
    return {"start": s, "end": e,
            "industries": list(INDUSTRIES.keys()),
            "counts": counts,
            "articles": arts[:300]}


@app.get("/api/keywords")
def api_keywords(period: str = "7d", start: str = "", end: str = "",
                 industry: str = "", limit: int = 40):
    from analysis.keywords import top_keywords
    s, e = resolve_period(period, start, end)
    conn = get_conn()
    arts = query_articles(conn, start_date=s, end_date=e,
                          industry=industry or None, limit=2000)
    conn.close()
    return {"start": s, "end": e, "keywords": top_keywords(arts, limit=limit)}


@app.get("/api/company")
def api_company(name: str = Query(..., min_length=1), period: str = "30d",
                start: str = "", end: str = ""):
    s, e = resolve_period(period, start, end)
    conn = get_conn()
    news = query_articles(conn, start_date=s, end_date=e, keyword=name, limit=200)
    conn.close()
    registry = query_company(name)
    site_items, site_note = fetch_company_news(name)
    return {"start": s, "end": e, "name": name,
            "registry": registry, "news": news,
            "site_news": site_items, "site_note": site_note}


@app.get("/api/status")
def api_status():
    conn = get_conn()
    st = latest_fetch_status(conn)
    conn.close()
    return {"sources": st}


@app.get("/api/export")
def api_export(period: str = "7d", start: str = "", end: str = "",
               company: str = ""):
    from report.word_report import build_report
    s, e = resolve_period(period, start, end)
    conn = get_conn()
    arts = query_articles(conn, start_date=s, end_date=e, limit=2000)
    status = latest_fetch_status(conn)
    conn.close()

    company_section = None
    title = "台灣產業趨勢監測報告"
    if company:
        conn = get_conn()
        news = query_articles(conn, start_date=s, end_date=e, keyword=company, limit=200)
        conn.close()
        site_items, site_note = fetch_company_news(company)
        company_section = {
            "name": company,
            "registry": query_company(company),
            "news": news + site_items,
            "site_note": site_note,
        }
        title = f"公司情報報告-{company}"
    try:
        path = build_report(arts, s, e, fetch_status=status,
                            title=title, company_section=company_section)
    except Exception as ex:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": str(ex)})
    return FileResponse(path, filename=Path(path).name,
                        media_type=("application/vnd.openxmlformats-officedocument"
                                    ".wordprocessingml.document"))
