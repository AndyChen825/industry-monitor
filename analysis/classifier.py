# -*- coding: utf-8 -*-
"""產業歸類:以關鍵字比對將文章對應到 11 大產業。

分類架構對照行政院主計總處「行業統計分類」,
對照說明見 config.INDUSTRIES 各項之 dgbas 欄位。
"""
from config import INDUSTRIES


def classify(title, summary=""):
    """回傳最符合的產業名稱;無法歸類回傳 None。

    計分:標題命中 1 關鍵字得 2 分,摘要命中得 1 分,取最高分產業。
    """
    text_title = title or ""
    text_summary = summary or ""
    best, best_score = None, 0
    for industry, spec in INDUSTRIES.items():
        score = 0
        for kw in spec["keywords"]:
            if kw in text_title:
                score += 2
            elif kw in text_summary:
                score += 1
        if score > best_score:
            best, best_score = industry, score
    return best


def classify_articles(items):
    """就地為文章清單補上 industry 欄位。"""
    for it in items:
        it["industry"] = classify(it.get("title", ""), it.get("summary", ""))
    return items
