# -*- coding: utf-8 -*-
"""商工登記公示資料查詢。

優先使用政府資料開放平臺 GCIS 開放 API(無驗證碼);
API 失敗時退回提供 findbiz 人工查詢連結。
findbiz 網頁版查詢有驗證碼與流量限制,不做網頁自動化查詢。
"""
import logging
import warnings
from urllib.parse import quote

import requests
import urllib3

from config import FETCH_TIMEOUT, USER_AGENT, GCIS_ALLOW_INSECURE_SSL

logger = logging.getLogger("fetcher.findbiz")

# 公司登記基本資料-應用一(依公司名稱關鍵字查詢)
GCIS_NAME_API = (
    "https://data.gcis.nat.gov.tw/od/data/api/6BBA2268-1367-4B42-9CCA-BC17419440A4"
    "?$format=json&$filter=Company_Name like {name} and Company_Status eq 01"
    "&$skip=0&$top=10"
)
# 公司登記基本資料(依統一編號查詢)
GCIS_BAN_API = (
    "https://data.gcis.nat.gov.tw/od/data/api/5F64D864-61CB-4D0D-8AD9-492047CC1EA6"
    "?$format=json&$filter=Business_Accounting_NO eq {ban}&$skip=0&$top=1"
)

FINDBIZ_MANUAL_URL = "https://findbiz.nat.gov.tw/fts/query/QueryBar/queryInit.do"


def _gcis_get(url):
    """GCIS 專用 GET。

    政府開放資料平臺憑證鏈缺少 Subject Key Identifier,Python 3.13 預設驗證會失敗;
    先嘗試正常驗證;失敗時僅在 config.GCIS_ALLOW_INSECURE_SSL=True 時
    對此政府網域降級略過憑證驗證(唯讀公開資料)並記錄警告,預設不降級。
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.exceptions.SSLError:
        if not GCIS_ALLOW_INSECURE_SSL:
            logger.warning(
                "GCIS 憑證驗證失敗;未啟用 GCIS_ALLOW_INSECURE_SSL,改提供人工查詢連結")
            return None
        logger.warning("GCIS 憑證驗證失敗,以不驗證模式重試(僅限 data.gcis.nat.gov.tw)")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT, verify=False)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.error("GCIS API 查詢失敗:%s", e)
            return None
    except requests.RequestException as e:
        logger.error("GCIS API 查詢失敗:%s", e)
        return None


def query_company(name_or_ban):
    """查詢公司登記資料。

    回傳 dict:
      {"status": "ok"/"fallback", "results": [...], "manual_url": ..., "note": ...}
    """
    name_or_ban = name_or_ban.strip()
    if name_or_ban.isdigit() and len(name_or_ban) == 8:
        url = GCIS_BAN_API.format(ban=name_or_ban)
    else:
        url = GCIS_NAME_API.format(name=quote(name_or_ban))

    resp = _gcis_get(url)
    if resp is not None:
        try:
            data = resp.json()
            results = []
            for row in data if isinstance(data, list) else []:
                results.append({
                    "統一編號": row.get("Business_Accounting_NO", ""),
                    "公司名稱": row.get("Company_Name", ""),
                    "負責人": row.get("Responsible_Name", ""),
                    "登記地址": row.get("Company_Location", ""),
                    "資本總額": row.get("Capital_Stock_Amount", ""),
                    "公司狀況": row.get("Company_Status_Desc", ""),
                    "核准設立日期": _fmt_date(row.get("Setup_Date")),
                    "最近變更日期": _fmt_date(row.get("Change_Of_Approval_Data")),
                })
            return {
                "status": "ok",
                "results": results,
                "manual_url": FINDBIZ_MANUAL_URL,
                "note": "資料來源:經濟部商業司 GCIS 開放資料 API。營業項目與完整變更紀錄請至商工登記公示查詢。",
            }
        except ValueError:
            logger.warning("GCIS API 回應非 JSON")

    return {
        "status": "fallback",
        "results": [],
        "manual_url": FINDBIZ_MANUAL_URL,
        "note": ("GCIS 開放 API 暫時無法查詢(可能為網路、憑證或服務問題;"
                 "憑證問題可參考 config.py 之 GCIS_ALLOW_INSECURE_SSL 說明)。"
                 "商工登記公示網頁查詢含驗證碼,無法自動化,請以人工方式查詢:"
                 + FINDBIZ_MANUAL_URL),
    }


def _fmt_date(v):
    """GCIS 日期為民國年 dict 或字串,轉為易讀格式。"""
    if isinstance(v, dict):
        y, m, d = v.get("year"), v.get("month"), v.get("day")
        if y:
            return f"民國{y}年{m}月{d}日"
    return str(v) if v else ""
