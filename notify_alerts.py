# -*- coding: utf-8 -*-
"""自動通知:負面聲量新警示 + 來源連續失敗 → 開 GitHub Issue(會寄 email)。

觸發條件:
- 負面警示:公司首次出現於警示清單、或篇數較上次通知倍增(且 ≥3 篇)
- 來源健康:應可抓取之來源連續 3 次失敗(同一來源 7 天內不重複通知)
狀態記錄於 data/alert_state.json(隨 workflow 提交,避免重複通知)。
無 GH_TOKEN 時為 dry-run(只列印、不發送、不寫狀態),供本機測試。
"""
import importlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
STATE_PATH = BASE / "data" / "alert_state.json"
META_PATH = BASE / "docs" / "data" / "meta.json"
TZ_TAIPEI = timezone(timedelta(hours=8))

MENTION = "@AndyChen825"
DASHBOARD = "https://andychen825.github.io/industry-monitor/"
CONSECUTIVE_FAILS = 3   # 來源連續失敗次數門檻
REALERT_DAYS = 7        # 同一來源重複通知間隔(天)
MIN_ALERT_COUNT = 3     # 負面警示最低篇數


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"alerted": {}, "sources": {}}


def collect_new_alerts(meta, state):
    current = {al["company"]: al for al in meta.get("alerts", [])}
    new_alerts = []
    for company, al in current.items():
        prev = state["alerted"].get(company, 0)
        if al["count"] >= MIN_ALERT_COUNT and (prev == 0 or al["count"] >= prev * 2):
            new_alerts.append(al)
            state["alerted"][company] = al["count"]
    # 已退出警示清單的公司移出狀態,未來再發生時可重新通知
    state["alerted"] = {c: n for c, n in state["alerted"].items() if c in current}
    return new_alerts


def collect_unhealthy_sources(state):
    from config import SOURCE_MODULES
    from db import get_conn
    today = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d")
    conn = get_conn()
    unhealthy = []
    for mod_name, display, _type in SOURCE_MODULES:
        try:
            mod = importlib.import_module(f"fetchers.{mod_name}")
        except ImportError:
            continue
        feeds = getattr(mod, "FEEDS", None)
        if feeds is not None and not feeds:
            continue  # 設計上即無法抓取之來源,不列入健康監控
        rows = conn.execute(
            "SELECT status FROM fetch_log WHERE source = ? ORDER BY id DESC LIMIT ?",
            (display, CONSECUTIVE_FAILS)).fetchall()
        if len(rows) >= CONSECUTIVE_FAILS and all(r[0] != "ok" for r in rows):
            last = state["sources"].get(display)
            if last:
                days = (datetime.strptime(today, "%Y-%m-%d")
                        - datetime.strptime(last, "%Y-%m-%d")).days
                if days < REALERT_DAYS:
                    continue
            unhealthy.append(display)
            state["sources"][display] = today
    conn.close()
    return unhealthy


def compose_body(new_alerts, unhealthy):
    now = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d %H:%M")
    lines = [f"{MENTION} 系統於 {now}(台北時間)偵測到以下事項:", ""]
    if new_alerts:
        lines.append("## ⚠ 負面聲量警示(新增/倍增)")
        lines.append("")
        for al in new_alerts:
            lines.append(f"### {al['company']} — 疑似負面 {al['count']} 篇"
                         f"(命中詞:{'、'.join(al['keywords'])})")
            for s in al["samples"][:3]:
                lines.append(f"- [{s['title']}]({s['url']})"
                             f"({s['source']},{s['published_at'] or '日期不明'})")
            lines.append("")
        lines.append("> 規則式偵測僅供初步示警,請點入報導人工確認。")
        lines.append("")
    if unhealthy:
        lines.append("## 🔌 來源連續失敗(近 3 次抓取均失敗)")
        lines.append("")
        for s in unhealthy:
            lines.append(f"- {s}(可能為 RSS 網址改版或網站阻擋,請檢查 fetchers/ 對應模組)")
        lines.append("")
    lines.append(f"[開啟儀表板]({DASHBOARD})")
    return "\n".join(lines)


def create_issue(title, body):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("=== DRY-RUN(無 GH_TOKEN,不發送、不寫狀態)===")
        print(title)
        print(body)
        return False
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body}, timeout=30)
    resp.raise_for_status()
    print("Issue 已建立:", resp.json().get("html_url"))
    return True


def main():
    if not META_PATH.exists():
        print("meta.json 不存在,略過通知")
        return
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    state = load_state()
    new_alerts = collect_new_alerts(meta, state)
    unhealthy = collect_unhealthy_sources(state)
    if not new_alerts and not unhealthy:
        print("無新警示、來源皆健康,不通知")
        # 仍保存狀態(維護 alerted 清單的進出)
        if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
            STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
        return
    parts = []
    if new_alerts:
        parts.append(f"負面警示 {len(new_alerts)} 家")
    if unhealthy:
        parts.append(f"來源異常 {len(unhealthy)} 個")
    title = f"【自動警示】{'、'.join(parts)} — {datetime.now(TZ_TAIPEI).strftime('%Y-%m-%d')}"
    sent = create_issue(title, compose_body(new_alerts, unhealthy))
    if sent:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                              encoding="utf-8")


if __name__ == "__main__":
    main()
