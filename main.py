# -*- coding: utf-8 -*-
"""台灣產業趨勢監測與公司情報系統 — 主流程。

用法:
  python main.py fetch [--sources cna,technews]   # 抓取(預設全部來源)
  python main.py report [--days 7]                # 產出期間報告
  python main.py weekly                           # 排程用:抓上週資料+產週報
  python main.py serve [--port 8000]              # 啟動網頁介面
"""
import argparse
import importlib
import logging
import sys
from datetime import datetime, timedelta, timezone

from config import SOURCE_MODULES, LOG_DIR
from db import get_conn, upsert_articles, log_fetch, query_articles, latest_fetch_status
from analysis.classifier import classify_articles

TZ_TAIPEI = timezone(timedelta(hours=8))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "run.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def run_fetch(only_sources=None):
    """逐一執行來源 fetcher;單一來源失敗不影響整體。回傳 (總新增筆數, 狀態列表)。"""
    conn = get_conn()
    total_new = 0
    statuses = []
    for mod_name, display, _stype in SOURCE_MODULES:
        if only_sources and mod_name not in only_sources:
            continue
        try:
            mod = importlib.import_module(f"fetchers.{mod_name}")
            items, errors = mod.fetch()
            items = classify_articles(items)
            new_count = upsert_articles(conn, items)
            total_new += new_count
            if items:
                status = "ok"
                msg = ";".join(errors)[:300] if errors else ""
            else:
                status = "error"
                msg = ";".join(errors)[:300] or "無資料"
            log_fetch(conn, display, status, new_count, msg)
            statuses.append((display, status, new_count, msg))
            logger.info("%s:%s,取得 %d 筆(新增 %d)%s",
                        display, status, len(items), new_count, f" | {msg}" if msg else "")
        except Exception as e:  # noqa: BLE001 — 單一來源任何錯誤都不可中斷整體
            log_fetch(conn, display, "error", 0, str(e)[:300])
            statuses.append((display, "error", 0, str(e)))
            logger.exception("%s 抓取失敗", display)
    conn.close()
    return total_new, statuses


def run_report(days=7, start=None, end=None, title=None):
    """產出期間 Word 報告,回傳檔案路徑。"""
    from report.word_report import build_report  # 延遲載入,fetch 不需要 docx

    now = datetime.now(TZ_TAIPEI)
    if not end:
        end = now.strftime("%Y-%m-%d")
    if not start:
        start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_conn()
    articles = query_articles(conn, start_date=start, end_date=end, limit=20000)
    # 等長前一期(供 SOV 變化對比)
    span = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days or 1
    prev_start = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=span)).strftime("%Y-%m-%d")
    articles_prev = query_articles(conn, start_date=prev_start, end_date=start, limit=20000)
    status = latest_fetch_status(conn)
    conn.close()
    try:
        from analysis.companies import build_watchlist
        watchlist = build_watchlist()
    except Exception:  # noqa: BLE001 — 名錄失敗時報告仍可產出(略過公司統計)
        watchlist = None
    path = build_report(articles, start, end, fetch_status=status,
                        title=title or "台灣產業趨勢監測報告", watchlist=watchlist,
                        articles_prev=articles_prev)
    logger.info("報告已產出:%s(%d 筆資料)", path, len(articles))
    return path


def run_weekly():
    """排程進入點:抓取 → 產出上週(週一至週日)週報。"""
    logger.info("=== 每週自動更新開始 ===")
    total_new, statuses = run_fetch()
    now = datetime.now(TZ_TAIPEI)
    last_monday = now - timedelta(days=now.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    path = run_report(start=last_monday.strftime("%Y-%m-%d"),
                      end=last_sunday.strftime("%Y-%m-%d"),
                      title="台灣產業趨勢監測週報")
    failed = [s for s in statuses if s[1] != "ok"]
    logger.info("=== 每週自動更新完成:新增 %d 筆;失敗來源 %d 個;報告:%s ===",
                total_new, len(failed), path)
    return path


def main():
    parser = argparse.ArgumentParser(description="台灣產業趨勢監測與公司情報系統")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="抓取所有(或指定)來源")
    p_fetch.add_argument("--sources", help="逗號分隔的來源模組名,如 cna,technews")

    p_report = sub.add_parser("report", help="產出期間報告")
    p_report.add_argument("--days", type=int, default=7)
    p_report.add_argument("--start")
    p_report.add_argument("--end")

    sub.add_parser("weekly", help="排程用:抓取+產出上週週報")

    p_serve = sub.add_parser("serve", help="啟動網頁介面")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    if args.cmd == "fetch":
        only = args.sources.split(",") if args.sources else None
        run_fetch(only)
    elif args.cmd == "report":
        print(run_report(days=args.days, start=args.start, end=args.end))
    elif args.cmd == "weekly":
        run_weekly()
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
