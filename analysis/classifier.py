# -*- coding: utf-8 -*-
"""產業歸類:以「產業關鍵字 + 公司觀察清單」計分,將文章對應到 11 大產業。

分類架構對照行政院主計總處「行業統計分類」,
對照說明見 config.INDUSTRIES 各項之 dgbas 欄位。
公司投票:文中提到觀察清單公司(如「宏碁」),即為該公司所屬產業加分,
避免「宏碁高層出入汽車旅館」因命中「旅館」而被誤歸住宿餐飲業。
"""
from config import INDUSTRIES, COMPANY_WATCHLIST
from analysis.companies import make_matcher

# (產業, 公司比對函式) — 模組載入時建立一次
_COMPANY_VOTES = [
    (industry, make_matcher(aliases))
    for industry, companies in COMPANY_WATCHLIST.items()
    for aliases in companies.values()
]


def classify(title, summary=""):
    """回傳最符合的產業名稱;無法歸類回傳 None。

    計分:產業關鍵字 標題命中 2 分/摘要 1 分;
         觀察清單公司 標題命中 2 分/摘要 1 分。取最高分產業。
    """
    text_title = title or ""
    text_summary = summary or ""
    scores = {}
    for industry, spec in INDUSTRIES.items():
        score = 0
        for kw in spec["keywords"]:
            if kw in text_title:
                score += 2
            elif kw in text_summary:
                score += 1
        if score:
            scores[industry] = scores.get(industry, 0) + score
    for industry, match in _COMPANY_VOTES:
        if match(text_title):
            scores[industry] = scores.get(industry, 0) + 2
        elif match(text_summary):
            scores[industry] = scores.get(industry, 0) + 1
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def classify_articles(items):
    """就地為文章清單補上 industry 欄位。"""
    for it in items:
        it["industry"] = classify(it.get("title", ""), it.get("summary", ""))
    return items
