# -*- coding: utf-8 -*-
"""公司名錄與聲量統計。

- 上市櫃全名錄(證交所/櫃買 OpenAPI)+ 手動品牌清單(config.COMPANY_WATCHLIST)
- 別名比對:中文子字串;英文完整單字、不分大小寫
- 供靜態網站(meta.watchlist)與 Word 報告(公司聲量統計)共用
"""
import json
import logging
import re

from config import BASE_DIR, COMPANY_WATCHLIST
from fetchers.base import http_get

logger = logging.getLogger("analysis.companies")

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

# 與日常用語/地名同形、或為其他更常見名稱之子字串的簡稱 → 排除
AMBIGUOUS_ABBRS = {
    "全台", "全新", "全國", "大眾", "中央", "國際", "亞洲", "第一", "中華",
    "台灣", "環球", "東方", "精英", "時代", "百達", "現代", "自然美",
    "大學", "光明", "南方", "太平洋", "文化", "健康", "數字", "商店",
    "台南", "南港", "冠軍", "幸福", "大量", "統一", "大成", "欣欣",
    "南亞", "聯發", "華電", "三星", "東森", "京城",
}

LISTED_CACHE = BASE_DIR / "data" / "listed_companies.json"

COMPANY_LIST_APIS = [
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",     # 上市
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",  # 上櫃
]

QUOTES_CACHE = BASE_DIR / "data" / "stock_quotes.json"

# 每日收盤行情(官方開放 API;盤中執行時取得的是最近一個交易日收盤)
QUOTE_APIS = [
    # (網址, 代號欄, 收盤欄, 漲跌欄)
    ("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
     "Code", "ClosingPrice", "Change"),
    ("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
     "SecuritiesCompanyCode", "Close", "Change"),
]


def _to_float(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def fetch_stock_quotes():
    """取得全體上市櫃最近收盤價與漲跌;失敗時退回快取。

    回傳 {股票代號: {"close": 收盤價, "pct": 漲跌幅%}}。
    """
    quotes = {}
    for url, code_key, close_key, change_key in QUOTE_APIS:
        resp = http_get(url, check_robots=False)  # 官方開放 API
        if resp is None:
            continue
        try:
            rows = resp.json()
        except ValueError:
            continue
        for row in rows:
            code = str(row.get(code_key, "")).strip()
            close = _to_float(row.get(close_key))
            change = _to_float(row.get(change_key))
            if not code or close is None or change is None:
                continue
            prev = close - change
            pct = (change / prev * 100) if prev else 0.0
            quotes[code] = {"close": close, "pct": round(pct, 2)}
    if quotes:
        QUOTES_CACHE.write_text(json.dumps(quotes, ensure_ascii=False), encoding="utf-8")
        return quotes
    if QUOTES_CACHE.exists():
        logger.warning("行情 API 失敗,使用上次快取")
        return json.loads(QUOTES_CACHE.read_text(encoding="utf-8"))
    return {}


def build_stock_quotes_by_abbr():
    """以公司簡稱為鍵之行情表:{簡稱: {"code", "close", "pct"}}。"""
    abbr_code = {}
    for row in fetch_listed_companies():
        abbr = str(row.get("公司簡稱", "")).strip()
        code = str(row.get("公司代號", "")).strip()
        if abbr and code and len(abbr) >= 2 and abbr not in AMBIGUOUS_ABBRS:
            abbr_code[abbr] = code
    quotes = fetch_stock_quotes()
    result = {}
    for abbr, code in abbr_code.items():
        q = quotes.get(code)
        if q:
            result[abbr] = {"code": code, "close": q["close"], "pct": q["pct"]}
    return result


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
        logger.warning("公司名錄 API 失敗,使用上次快取")
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
    for industry, companies in COMPANY_WATCHLIST.items():
        bucket = watchlist.setdefault(industry, {})
        for name, aliases in companies.items():
            bucket[name] = sorted(set(bucket.get(name, [])) | set(aliases))
    return watchlist


_HAN_RE = re.compile(r"[一-鿿]")


def make_matcher(aliases):
    """建立別名比對函式:中文子字串;英文完整單字不分大小寫。"""
    zh = [a for a in aliases if _HAN_RE.search(a)]
    latin = [re.compile(r"(^|[^A-Za-z0-9])" + re.escape(a) + r"([^A-Za-z0-9]|$)", re.I)
             for a in aliases if not _HAN_RE.search(a)]

    def match(text):
        return any(a in text for a in zh) or any(r.search(text) for r in latin)
    return match


def company_counts(articles, watchlist, top_n=10):
    """統計各產業之公司聲量。

    回傳 {產業: [(公司, 篇數), ...]}(依篇數排序,取前 top_n);
    比對範圍為文章之標題+摘要+來源,不限文章本身的產業分類。
    """
    result = {}
    for industry, companies in watchlist.items():
        matchers = [(name, make_matcher(aliases)) for name, aliases in companies.items()]
        counts = {}
        for a in articles:
            text = f"{a.get('title', '')} {a.get('summary', '')} {a.get('source', '')}"
            for name, match in matchers:
                if match(text):
                    counts[name] = counts.get(name, 0) + 1
        ranked = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
        if ranked:
            result[industry] = ranked
    return result
