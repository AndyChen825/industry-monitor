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
from analysis.keywords import article_words, top_from_wordsets, rising_words
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

    # 文章資料檔分層(控制下載量):
    # - articles.json:近 7 天完整欄位(預設載入,開頁快)
    # - articles_full.json:完整歷史(切換至 30/90 天/YTD 時才背景載入);
    #   30 天前僅保留可歸類文章且不含摘要
    cut7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    cut30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    def _slim(a, with_summary=True):
        return {
            "title": a["title"],
            "summary": (a.get("summary") or "")[:80] if with_summary else "",
            "source": a["source"],
            "url": a["url"],
            "published_at": a.get("published_at") or "",
            "industry": a.get("industry"),
        }

    core = [_slim(a) for a in articles if (a.get("published_at") or "") >= cut7]
    full = []
    for a in articles:
        d = a.get("published_at") or ""
        if d >= cut30:
            full.append(_slim(a))
        elif a.get("industry"):
            full.append(_slim(a, with_summary=False))
    (DATA_DIR / "articles.json").write_text(
        json.dumps(core, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "articles_full.json").write_text(
        json.dumps(full, ensure_ascii=False), encoding="utf-8")
    slim = full  # 供後續統計沿用

    # 每日各產業篇數(供前端 KPI/產業計數/週對週,不需載入全文)
    daily = {}
    for a in articles:
        d = (a.get("published_at") or "")[:10]
        if not d:
            continue
        bucket = daily.setdefault(d, {"_total": 0})
        bucket["_total"] += 1
        ind = a.get("industry")
        if ind:
            bucket[ind] = bucket.get(ind, 0) + 1

    # 各預設期間之關鍵字詞頻(文字雲)+ 竄升詞(本期 vs 等長前期)
    # 先對全部文章做一次斷詞,之後各期間/產業子集合以集合運算統計,避免重複斷詞
    seg = [(article_words(a), a.get("industry"), a.get("published_at") or "")
           for a in articles]

    def window(start_s, end_s=None):
        return [(w, ind) for w, ind, d in seg
                if d >= start_s and (end_s is None or d < end_s)]

    presets = {"7d": 7, "30d": 30, "90d": 90}
    keywords = {}
    for key, days in presets.items():
        cur_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        prev_start = (now - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        group = {}
        for scope in ["all"] + list(INDUSTRIES):
            cur = [(w, i) for w, i in window(cur_start)
                   if scope == "all" or i == scope]
            if not cur:
                continue
            prev = [(w, i) for w, i in window(prev_start, cur_start)
                    if scope == "all" or i == scope]
            # 前期資料量不足(冷啟動期)時,成長倍數無意義 → 不提供竄升詞
            enough_prev = len(prev) >= max(20, len(cur) * 0.3)
            group[scope] = {
                "top": top_from_wordsets(cur, limit=40),
                "rising": rising_words(cur, prev) if enough_prev else [],
            }
        keywords[key] = group
    # YTD:無等長前期可比,僅提供 top 詞
    ytd_start = now.replace(month=1, day=1).strftime("%Y-%m-%d")
    ytd_group = {}
    for scope in ["all"] + list(INDUSTRIES):
        cur = [(w, i) for w, i in window(ytd_start) if scope == "all" or i == scope]
        if cur:
            ytd_group[scope] = {"top": top_from_wordsets(cur, limit=40), "rising": []}
    keywords["ytd"] = ytd_group
    (DATA_DIR / "keywords.json").write_text(
        json.dumps(keywords, ensure_ascii=False), encoding="utf-8")

    watchlist = build_watchlist()

    # 品牌關聯字:近 90 天內提及 ≥3 篇之公司,統計其報導中最常共同出現的詞
    # (排除公司自身別名;供公司搜尋頁顯示「媒體把這家公司跟什麼綁在一起」)
    from analysis.companies import make_matcher
    texts = [f"{a['title']} {a.get('summary') or ''} {a.get('source') or ''}"
             for a in articles]
    company_aliases = {}
    for comps in watchlist.values():
        for name, aliases in comps.items():
            company_aliases.setdefault(name, set()).update(aliases)
    assoc = {}
    cut90 = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    for name, aliases in company_aliases.items():
        match = make_matcher(sorted(aliases))
        hits = [(seg[i][0], seg[i][1]) for i in range(len(articles))
                if seg[i][2] >= cut90 and match(texts[i])]
        if len(hits) < 3:
            continue
        top = top_from_wordsets(hits, limit=25)
        out = [w for w in top
               if not any(w["word"] in al or al in w["word"] for al in aliases)][:12]
        if out:
            assoc[name] = [{"word": w["word"], "count": w["count"]} for w in out]

    # 當週 Word 報告:僅於週一產出(或設 FORCE_REPORT=1 強制、或尚無任何報告時)
    import os
    existing = list(REPORTS_DIR.glob("*.docx"))
    if now.weekday() == 0 or os.environ.get("FORCE_REPORT") == "1" or not existing:
        from report.word_report import build_report
        start_s = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_s = now.strftime("%Y-%m-%d")
        prev_start_s = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        week_arts = query_articles(conn, start_date=start_s, end_date=end_s, limit=20000)
        prev_arts = query_articles(conn, start_date=prev_start_s, end_date=start_s, limit=20000)
        report_name = f"台灣產業趨勢監測週報_{start_s}_{end_s}.docx"
        build_report(week_arts, start_s, end_s, fetch_status=status,
                     title="台灣產業趨勢監測週報", out_path=REPORTS_DIR / report_name,
                     watchlist=watchlist, articles_prev=prev_arts)
        print(f"週報已產出:{report_name}")
        try:
            from report.ppt_report import build_ppt
            ppt_name = f"台灣產業趨勢監測週報_{start_s}_{end_s}.pptx"
            build_ppt(week_arts, start_s, end_s, watchlist=watchlist,
                      out_path=str(REPORTS_DIR / ppt_name), articles_prev=prev_arts)
            print(f"簡報已產出:{ppt_name}")
        except Exception as e:  # noqa: BLE001 — PPT 失敗不影響 Word 週報
            print(f"簡報產出失敗(不影響 Word 週報):{e}")
    else:
        print("非週一,僅更新資料,不產出新週報")
    conn.close()

    # 每種格式各保留最近 N 份報告
    kept = []
    for pattern in ("*.docx", "*.pptx"):
        files = sorted(REPORTS_DIR.glob(pattern),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[KEEP_REPORTS:]:
            old.unlink()
        kept.extend(files[:KEEP_REPORTS])
    report_files = [p.name for p in
                    sorted(kept, key=lambda p: p.stat().st_mtime, reverse=True)]

    # meta:產出時間、來源狀態、報告清單
    meta = {
        "generated_at": now.isoformat(timespec="seconds"),
        "article_count": len(slim),
        "fetch_status": status,
        "reports": report_files,
        "watchlist": watchlist,
        "daily": daily,
    }
    # 上市櫃最近收盤價與漲跌幅(附行情所屬日期)
    meta["quotes"], meta["quotes_date"] = build_stock_quotes_by_abbr()

    # 負面聲量警示 + 商機訊號(近 7 天,規則式初步偵測)
    from analysis.alerts import negative_alerts, positive_signals
    alert_cut = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [a for a in articles if (a.get("published_at") or "") >= alert_cut]
    meta["alerts"] = negative_alerts(recent)
    meta["opportunities"] = positive_signals(recent)
    meta["assoc"] = assoc   # 品牌關聯字(近 90 天)

    # 產品線監測組 + 標案雷達
    from config import PRODUCT_LINES, TENDER_KEYWORDS, LAUNCH_KEYWORDS
    meta["product_lines"] = PRODUCT_LINES
    meta["launch_keywords"] = LAUNCH_KEYWORDS
    from fetchers.tenders import fetch_tenders, MANUAL_URL
    tender_records, tender_note = fetch_tenders(TENDER_KEYWORDS)
    meta["tenders"] = {"records": tender_records, "note": tender_note,
                       "keywords": TENDER_KEYWORDS, "manual_url": MANUAL_URL}
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
