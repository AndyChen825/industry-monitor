# -*- coding: utf-8 -*-
"""Word 報告產生器(python-docx)。

結構:封面 → 執行摘要(附出處) → 各產業動態 → 建議策略(標明 AI 分析)
     → 資料缺口說明 → 附錄:引用來源總表。
"""
from datetime import datetime, timezone, timedelta

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

from config import INDUSTRIES, REPORT_DIR
from analysis.summarizer import summarize_period, detect_themes, format_citation

TZ_TAIPEI = timezone(timedelta(hours=8))

MAIN_COLOR = RGBColor(0x1F, 0x4E, 0x79)   # 深藍標題
GRAY = RGBColor(0x66, 0x66, 0x66)


def _set_base_font(doc):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    # 中文字型
    style.element.rPr.rFonts.set(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", "微軟正黑體")


def _heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = MAIN_COLOR
    return h


def _cite_para(doc, article, bullet=True):
    """一則條目:標題 + 出處(媒體、日期、連結)。"""
    p = doc.add_paragraph(style="List Bullet" if bullet else None)
    p.add_run(article["title"])
    cite = p.add_run(" " + format_citation(article))
    cite.font.size = Pt(9)
    cite.font.color.rgb = GRAY
    return p


def build_report(articles, start_date, end_date, fetch_status=None,
                 title="台灣產業趨勢監測週報", company_section=None, out_path=None):
    """產出 Word 報告,回傳檔案路徑。

    articles:期間內文章(dict list,含 industry 欄位)
    fetch_status:各來源最近抓取狀態(標示資料缺口)
    company_section:公司情報 dict(公司報告用),含 name/registry/news
    """
    doc = Document()
    _set_base_font(doc)
    now = datetime.now(TZ_TAIPEI)

    # ---- 封面 ----
    for _ in range(6):
        doc.add_paragraph()
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = tp.add_run(title)
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = MAIN_COLOR
    for text in (f"報告期間:{start_date} ~ {end_date}",
                 f"產出日期:{now.strftime('%Y-%m-%d %H:%M')}(台北時間)",
                 "資料來源:公開新聞媒體 RSS、經濟部商工登記開放資料"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = p.add_run(text)
        rr.font.size = Pt(12)
        rr.font.color.rgb = GRAY
    doc.add_page_break()

    # ---- 執行摘要 ----
    _heading(doc, "壹、執行摘要", 1)
    by_ind = summarize_period(articles, top_n=3)
    if not by_ind:
        doc.add_paragraph("本期間內未取得可歸類之產業新聞資料 —— 資料不足。")
    else:
        doc.add_paragraph(
            f"本期間共蒐集 {len(articles)} 筆公開報導,可歸類至 "
            f"{len(by_ind)} 個產業類別。各產業重點如下(每點附出處):")
        for ind in INDUSTRIES:
            arts = by_ind.get(ind)
            if not arts:
                continue
            p = doc.add_paragraph()
            p.add_run(f"【{ind}】").bold = True
            for a in arts[:2]:
                _cite_para(doc, a)

    # ---- 公司情報(公司報告專用) ----
    if company_section:
        doc.add_page_break()
        _heading(doc, f"貳、公司情報:{company_section['name']}", 1)
        reg = company_section.get("registry") or {}
        _heading(doc, "一、商工登記資料", 2)
        if reg.get("results"):
            table = doc.add_table(rows=0, cols=2)
            table.style = "Light Grid Accent 1"
            for comp in reg["results"][:3]:
                for k, v in comp.items():
                    row = table.add_row()
                    row.cells[0].text = k
                    row.cells[1].text = str(v)
                table.add_row()
        else:
            doc.add_paragraph("未能自動取得商工登記資料 —— 資料不足。")
        note = reg.get("note")
        if note:
            np_ = doc.add_paragraph(note)
            np_.runs[0].font.size = Pt(9)
            np_.runs[0].font.color.rgb = GRAY
        _heading(doc, "二、相關報導與公告", 2)
        news = company_section.get("news") or []
        if news:
            for a in news[:20]:
                _cite_para(doc, a)
        else:
            doc.add_paragraph("期間內未蒐集到該公司相關報導 —— 資料不足。")
        site_note = company_section.get("site_note")
        if site_note:
            sp = doc.add_paragraph("官網公告限制:" + site_note)
            sp.runs[0].font.size = Pt(9)
            sp.runs[0].font.color.rgb = GRAY

    # ---- 各產業動態 ----
    doc.add_page_break()
    _heading(doc, "參、各產業動態摘要" if company_section else "貳、各產業動態摘要", 1)
    by_ind_full = summarize_period(articles, top_n=8)
    for ind, spec in INDUSTRIES.items():
        _heading(doc, ind, 2)
        dg = doc.add_paragraph(f"主計總處行業統計分類對照:{spec['dgbas']}")
        dg.runs[0].font.size = Pt(9)
        dg.runs[0].font.color.rgb = GRAY
        arts = by_ind_full.get(ind)
        if not arts:
            doc.add_paragraph("本期間無可歸類至此產業之報導 —— 資料不足。")
            continue
        for a in arts:
            _cite_para(doc, a)

    # ---- 建議策略 ----
    doc.add_page_break()
    _heading(doc, "肆、建議策略" if company_section else "參、建議策略", 1)
    disclaimer = doc.add_paragraph(
        "以下為系統依據期間內報導之主題統計所產生之策略觀察,屬 AI 分析,僅供參考,"
        "不構成投資或經營建議;每項觀察附代表性報導出處。")
    disclaimer.runs[0].font.color.rgb = GRAY
    themes = detect_themes(articles)
    if not themes:
        doc.add_paragraph("期間內資料量不足以形成跨產業主題觀察 —— 資料不足。")
    else:
        for theme, count, advice, samples in themes:
            p = doc.add_paragraph(style="List Number")
            p.add_run(f"{theme}(本期相關報導 {count} 篇):").bold = True
            p.add_run(advice)
            for s in samples:
                sp = doc.add_paragraph(style="List Bullet 2")
                sp.add_run(s["title"])
                c = sp.add_run(" " + format_citation(s))
                c.font.size = Pt(9)
                c.font.color.rgb = GRAY

    # ---- 資料缺口 ----
    if fetch_status:
        gaps = [s for s in fetch_status if s["status"] != "ok"]
        if gaps:
            _heading(doc, "資料缺口說明", 1)
            doc.add_paragraph("下列來源於本次更新未能成功抓取,相關產業之涵蓋度可能不足:")
            for g in gaps:
                doc.add_paragraph(
                    f"{g['source']}:{g['status']}({g.get('message') or '無訊息'},"
                    f"時間 {g['run_at']})", style="List Bullet")

    # ---- 附錄:引用來源總表 ----
    doc.add_page_break()
    _heading(doc, "附錄:引用來源總表", 1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, t in enumerate(("來源媒體", "標題", "發布日期", "原文連結")):
        hdr[i].text = t
    cited = {a["url"]: a for a in articles if a.get("industry")}
    for a in sorted(cited.values(), key=lambda x: (x["source"], x.get("published_at") or "")):
        row = table.add_row().cells
        row[0].text = a["source"]
        row[1].text = a["title"][:60]
        row[2].text = (a.get("published_at") or "")[:10]
        row[3].text = a["url"]
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8)

    # ---- 輸出 ----
    if out_path is None:
        fname = f"{title}_{start_date}_{end_date}_{now.strftime('%Y%m%d%H%M')}.docx"
        out_path = REPORT_DIR / fname
    doc.save(out_path)
    return str(out_path)
