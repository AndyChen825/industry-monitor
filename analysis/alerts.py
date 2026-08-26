# -*- coding: utf-8 -*-
"""負面聲量警示(規則式)。

掃描期間內文章:同時命中「觀察名單公司(手動清單)」與「負面關鍵詞」
即列入警示。屬規則式初步偵測(如『資安展』不會、『駭客』會命中),
所有輸出均需標明僅供初步示警、應人工確認。
"""
from config import COMPANY_WATCHLIST, NEGATIVE_KEYWORDS
from analysis.companies import make_matcher

# 主管機關/政府單位:負面詞多為其「執法行為」(裁罰他人)而非自身事件,不列入警示
ALERT_EXCLUDE = {"金管會", "教育部", "國科會", "中研院"}


def _company_matchers():
    seen = set()
    matchers = []
    for companies in COMPANY_WATCHLIST.values():
        for name, aliases in companies.items():
            if name in seen or name in ALERT_EXCLUDE:
                continue
            seen.add(name)
            matchers.append((name, make_matcher(aliases)))
    return matchers


def signal_scan(articles, keywords, max_samples=5):
    """通用訊號掃描:觀察名單公司 × 指定關鍵詞同時命中。

    回傳 [{"company", "count", "keywords", "samples"}],依命中篇數排序。
    """
    matchers = _company_matchers()
    hits_by_company = {}
    for a in articles:
        text = f"{a.get('title', '')} {a.get('summary', '')}"
        hit_kws = [k for k in keywords if k in text]
        if not hit_kws:
            continue
        full = text + " " + (a.get("source") or "")
        for name, match in matchers:
            if not match(full):
                continue
            item = hits_by_company.setdefault(name, {
                "company": name, "count": 0, "keywords": set(), "samples": [],
            })
            item["count"] += 1
            item["keywords"].update(hit_kws)
            if len(item["samples"]) < max_samples:
                item["samples"].append({
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", ""),
                    "published_at": (a.get("published_at") or "")[:10],
                })
    out = []
    for v in hits_by_company.values():
        v["keywords"] = sorted(v["keywords"])[:6]
        out.append(v)
    out.sort(key=lambda x: -x["count"])
    return out


def negative_alerts(articles, max_samples=5):
    """負面聲量警示。"""
    return signal_scan(articles, NEGATIVE_KEYWORDS, max_samples)


def positive_signals(articles, max_samples=5):
    """商機(正面)訊號:得標/擴廠/展店/導入AI 等,供業務拜訪線索。"""
    from config import POSITIVE_KEYWORDS
    return signal_scan(articles, POSITIVE_KEYWORDS, max_samples)
