# -*- coding: utf-8 -*-
"""SQLite 資料層:文章儲存(增量更新)、抓取紀錄。"""
import sqlite3
from datetime import datetime, timezone, timedelta

from config import DB_PATH

TZ_TAIPEI = timezone(timedelta(hours=8))

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    summary      TEXT,
    source       TEXT NOT NULL,          -- 來源媒體顯示名稱
    source_type  TEXT,                   -- 綜合新聞 / 財經專業 / 深度雜誌 / 科技新創 / 企業官網
    url          TEXT NOT NULL UNIQUE,   -- 原文連結(去重複依據)
    published_at TEXT,                   -- ISO 8601
    industry     TEXT,                   -- 歸類後的 11 大產業;未能歸類為 NULL
    fetched_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_industry  ON articles(industry);

CREATE TABLE IF NOT EXISTS fetch_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at     TEXT NOT NULL,
    source     TEXT NOT NULL,
    status     TEXT NOT NULL,            -- ok / error / skipped
    new_items  INTEGER DEFAULT 0,
    message    TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def now_iso():
    return datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")


def upsert_articles(conn, items):
    """插入文章,以 url 去重;回傳實際新增筆數。"""
    new_count = 0
    for it in items:
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO articles
                   (title, summary, source, source_type, url, published_at, industry, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    it["title"], it.get("summary", ""), it["source"],
                    it.get("source_type", ""), it["url"],
                    it.get("published_at"), it.get("industry"), now_iso(),
                ),
            )
            new_count += cur.rowcount
        except sqlite3.Error:
            continue
    conn.commit()
    return new_count


def log_fetch(conn, source, status, new_items=0, message=""):
    conn.execute(
        "INSERT INTO fetch_log (run_at, source, status, new_items, message) VALUES (?,?,?,?,?)",
        (now_iso(), source, status, new_items, message),
    )
    conn.commit()


def query_articles(conn, start_date=None, end_date=None, industry=None, keyword=None, limit=500):
    """依期間 / 產業 / 關鍵字(公司名)查詢。日期為 YYYY-MM-DD 字串。"""
    sql = "SELECT * FROM articles WHERE 1=1"
    args = []
    if start_date:
        sql += " AND published_at >= ?"
        args.append(start_date)
    if end_date:
        sql += " AND published_at <= ?"
        args.append(end_date + "T23:59:59+08:00")
    if industry:
        sql += " AND industry = ?"
        args.append(industry)
    if keyword:
        sql += " AND (title LIKE ? OR summary LIKE ? OR source LIKE ?)"
        args.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    sql += " ORDER BY published_at DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def latest_fetch_status(conn):
    """每個來源最近一次抓取狀態,供報告標示資料缺口。"""
    rows = conn.execute(
        """SELECT source, status, run_at, new_items, message FROM fetch_log
           WHERE id IN (SELECT MAX(id) FROM fetch_log GROUP BY source)
           ORDER BY source"""
    ).fetchall()
    return [dict(r) for r in rows]
