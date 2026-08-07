# -*- coding: utf-8 -*-
"""摘要與策略生成(可溯源)。

原則:
- 所有摘要條目皆直接取自資料庫中的文章(標題+摘要),並附來源媒體、日期、連結。
- 不生成無出處的內容;某產業於期間內無資料時,明確標示「資料不足」。
- 策略建議為規則式主題偵測(統計關鍵詞出現頻率)產生之觀察,
  於報告中標明「AI 分析,僅供參考」,且每項觀察列出依據之文章數。
"""
from collections import Counter

# 跨產業主題偵測:主題 → (關鍵詞, 策略觀察模板)
THEMES = {
    "AI 與自動化": (
        ["AI", "人工智慧", "生成式", "自動化", "機器人", "大語言模型"],
        "AI 相關動態密集,建議評估 AI 於自身營運與產品線之導入機會,並關注算力、人才與資料治理布局。",
    ),
    "地緣政治與供應鏈": (
        ["關稅", "地緣", "供應鏈", "出口管制", "制裁", "移轉", "赴美", "設廠"],
        "地緣政治與供應鏈重組訊號明顯,建議檢視供應鏈集中度風險,評估多元布局與在地化策略。",
    ),
    "利率與資金環境": (
        ["升息", "降息", "利率", "通膨", "匯率", "資金"],
        "利率與匯率變動訊號頻繁,建議加強財務避險與資金成本管理,留意央行政策走向。",
    ),
    "永續與能源": (
        ["碳", "淨零", "ESG", "綠電", "再生能源", "永續"],
        "永續與能源議題持續升溫,建議盤點碳盤查與綠電採購進度,將 ESG 納入中期策略。",
    ),
    "人力與人口結構": (
        ["缺工", "少子化", "高齡", "人才", "薪資", "移工"],
        "人力結構議題受關注,建議強化人才留任與自動化替代方案,評估高齡/少子化對需求端的影響。",
    ),
    "資安與法遵": (
        ["資安", "個資", "駭客", "法遵", "洗錢", "金管會裁罰"],
        "資安與法遵事件頻傳,建議檢視資安投資與法遵框架,降低營運中斷與裁罰風險。",
    ),
}

MIN_THEME_HITS = 3  # 主題至少命中文章數才納入策略觀察


def summarize_period(articles, top_n=8):
    """產出執行摘要條目(每產業取重點文章)。

    回傳 {industry: [article, ...]};以「發布時間新 + 摘要完整」排序。
    """
    by_industry = {}
    for a in articles:
        ind = a.get("industry")
        if not ind:
            continue
        by_industry.setdefault(ind, []).append(a)
    result = {}
    for ind, arts in by_industry.items():
        arts_sorted = sorted(
            arts,
            key=lambda x: ((x.get("published_at") or ""), len(x.get("summary") or "")),
            reverse=True,
        )
        # 同一來源最多取 3 篇,避免單一媒體壟斷版面
        picked, per_source = [], Counter()
        for a in arts_sorted:
            if per_source[a["source"]] >= 3:
                continue
            picked.append(a)
            per_source[a["source"]] += 1
            if len(picked) >= top_n:
                break
        result[ind] = picked
    return result


def detect_themes(articles):
    """跨產業主題偵測,回傳 [(主題, 命中文章數, 策略觀察, 代表文章列表)]。"""
    findings = []
    for theme, (kws, advice) in THEMES.items():
        hits = [
            a for a in articles
            if any(kw in (a.get("title") or "") or kw in (a.get("summary") or "") for kw in kws)
        ]
        if len(hits) >= MIN_THEME_HITS:
            hits_sorted = sorted(hits, key=lambda x: x.get("published_at") or "", reverse=True)
            findings.append((theme, len(hits), advice, hits_sorted[:3]))
    findings.sort(key=lambda t: t[1], reverse=True)
    return findings


def format_citation(article):
    """出處標記:媒體名 + 日期 + 連結。"""
    date = (article.get("published_at") or "")[:10] or "日期不明"
    return f"({article['source']},{date},{article['url']})"
