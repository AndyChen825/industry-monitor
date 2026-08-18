# -*- coding: utf-8 -*-
"""報告用圖表(matplotlib → PNG,供 Word 內嵌)。"""
import tempfile
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt, font_manager  # noqa: E402


def _setup_font():
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Microsoft JhengHei", "Noto Sans CJK TC", "Noto Sans TC",
                 "Noto Sans CJK JP", "Noto Sans CJK SC"):
        if cand in names:
            plt.rcParams["font.family"] = cand
            return
    # 找不到中文字型時仍可出圖(中文會缺字),不中斷報告


_setup_font()
plt.rcParams["axes.unicode_minus"] = False

BLUE = "#2a78d6"


def industry_bar_png(ind_counts):
    """各產業報導篇數橫條圖,回傳 PNG 路徑。"""
    items = sorted(ind_counts.items(), key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(names, vals, color=BLUE, height=0.62)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v}", va="center", fontsize=9, color="#333333")
    ax.set_title("各產業報導篇數", fontsize=12)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path)
    plt.close(fig)
    return path


def daily_trend_png(articles, start_s, end_s):
    """期間內每日報導量折線圖,回傳 PNG 路徑。"""
    days = []
    d = datetime.strptime(start_s, "%Y-%m-%d")
    end = datetime.strptime(end_s, "%Y-%m-%d")
    while d <= end:
        days.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    daily = {dd: 0 for dd in days}
    for a in articles:
        dd = (a.get("published_at") or "")[:10]
        if dd in daily:
            daily[dd] += 1
    fig, ax = plt.subplots(figsize=(8, 3), dpi=150)
    ax.plot(range(len(days)), [daily[dd] for dd in days],
            color=BLUE, linewidth=2, marker="o", markersize=4)
    step = max(1, len(days) // 10)
    ax.set_xticks(range(0, len(days), step))
    ax.set_xticklabels([days[i][5:] for i in range(0, len(days), step)], fontsize=8)
    ax.set_title("每日報導量趨勢", fontsize=12)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path = tempfile.mktemp(suffix=".png")
    fig.savefig(path)
    plt.close(fig)
    return path
