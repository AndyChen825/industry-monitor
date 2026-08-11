# -*- coding: utf-8 -*-
"""關鍵字詞頻統計(文字雲資料來源)。

以 jieba 對期間內文章之標題+摘要斷詞,過濾停用詞與單字詞後統計詞頻。
"""
from collections import Counter

import jieba

# 台灣常見專有名詞,避免被錯誤切分(如「民進黨」→「民進」+「黨」)
CUSTOM_WORDS = [
    "民進黨", "國民黨", "民眾黨", "行政院", "立法院", "金管會", "主計總處",
    "台積電", "聯發科", "鴻海", "中華電信", "國泰金", "富邦金", "中央銀行",
    "半導體", "供應鏈", "資料中心", "生成式AI", "少子化", "都更", "碳費",
]
for _w in CUSTOM_WORDS:
    jieba.add_word(_w)

# 停用詞:通用虛詞 + 新聞媒體慣用詞(避免「報導」「記者」洗版)
STOPWORDS = set("""
的 了 在 是 我 有 和 就 不 人 都 一 一個 上 也 很 到 說 要 去 你 會 著 沒有 看 好
自己 這 那 他 她 它 們 與 及 或 但 而 被 讓 從 向 對 於 之 其 中 並 等 以 為 將 已
今天 昨天 明天 目前 表示 指出 認為 強調 提到 透露 報導 記者 綜合 電子報 新聞網
中央社 自由時報 台北 快訊 獨家 影音 圖輯 一覽 更新 首次 上稿 時間 相關 進行 可能
因為 所以 如果 由於 因此 這些 那些 沒 還 再 又 才 只 個 家 名 位 歲 年 月 日 時
分 秒 元 億 萬 千 百 點 我們 他們 什麼 怎麼 這樣 那樣 已經 正在 開始 持續 最新
日電 外電 專電 綜合 綜合報導 財經頻道 億元 萬元 兆元 台幣 新台幣 美元 日圓
今日 昨日 明日 上午 下午 晚間 凌晨 消息 影片 訂閱 內容 詳見 請見 更多 一次
頻道 公布 提供 舉行 出席 召開 發布 發表 宣布 針對 收盤 開盤 上漲 下跌 財經
""".split())


def article_words(article):
    """單篇文章斷詞(去重、濾停用詞),供大量子集合統計時預先計算。"""
    text = (article.get("title") or "") + " " + (article.get("summary") or "")
    words = set()
    for w in jieba.cut(text):
        w = w.strip()
        if len(w) < 2 or w in STOPWORDS:
            continue
        if not any("一" <= ch <= "鿿" or ch.isalpha() for ch in w):
            continue
        words.add(w)
    return words


def top_from_wordsets(wordsets, limit=40):
    """由預先斷詞的 [(words, industry)] 統計詞頻。回傳格式同 top_keywords。"""
    counter = Counter()
    industry_votes = {}
    for words, ind in wordsets:
        for w in words:
            counter[w] += 1
            if ind:
                industry_votes.setdefault(w, Counter())[ind] += 1
    result = []
    for w, cnt in counter.most_common(limit):
        votes = industry_votes.get(w)
        main_ind = votes.most_common(1)[0][0] if votes else None
        result.append({"word": w, "count": cnt, "industry": main_ind})
    return result


def rising_words(cur_wordsets, prev_wordsets, limit=12, min_count=3, min_growth=0.5):
    """竄升關鍵字:本期相較前一期成長最快的詞。

    回傳 [{"word", "count", "prev", "growth", "industry"}],
    growth = (本期-前期)/max(前期,1),僅收本期 ≥ min_count 且成長 > min_growth 者。
    """
    cur = {w["word"]: w for w in top_from_wordsets(cur_wordsets, limit=300)}
    prev = {w["word"]: w["count"] for w in top_from_wordsets(prev_wordsets, limit=300)}
    out = []
    for word, info in cur.items():
        c = info["count"]
        if c < min_count:
            continue
        p = prev.get(word, 0)
        growth = (c - p) / max(p, 1)
        if growth <= min_growth:
            continue
        out.append({"word": word, "count": c, "prev": p,
                    "growth": round(growth, 2), "industry": info.get("industry")})
    out.sort(key=lambda x: (-x["growth"], -x["count"]))
    return out[:limit]


def top_keywords(articles, limit=40):
    """回傳 [(詞, 次數, 主要產業)],依詞頻排序。

    主要產業:該詞出現次數最多的產業分類(供前端著色/篩選提示)。
    """
    counter = Counter()
    industry_votes = {}
    for a in articles:
        text = (a.get("title") or "") + " " + (a.get("summary") or "")
        ind = a.get("industry")
        seen_in_doc = set()
        for w in jieba.cut(text):
            w = w.strip()
            if len(w) < 2 or w in STOPWORDS:
                continue
            if not any("一" <= ch <= "鿿" or ch.isalpha() for ch in w):
                continue
            # 同一篇文章同一詞只計一次,避免單篇重複灌詞
            if w in seen_in_doc:
                continue
            seen_in_doc.add(w)
            counter[w] += 1
            if ind:
                industry_votes.setdefault(w, Counter())[ind] += 1
    result = []
    for w, cnt in counter.most_common(limit):
        votes = industry_votes.get(w)
        main_ind = votes.most_common(1)[0][0] if votes else None
        result.append({"word": w, "count": cnt, "industry": main_ind})
    return result
