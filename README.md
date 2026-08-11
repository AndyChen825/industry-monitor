# 台灣產業趨勢監測與公司情報系統

追蹤 11 大產業重大動態、政策與市場變化,產出**附出處**的文字摘要與策略建議。提供本機網頁介面、Word 報告匯出,並支援每週一 12:00 自動更新。

## 系統架構

```
industry-monitor/
├── main.py               # 一鍵執行:fetch / report / weekly / serve
├── config.py             # 產業分類對照(主計總處)、來源註冊表、抓取參數
├── db.py                 # SQLite 資料層(增量更新、以連結去重)
├── fetchers/             # 各來源獨立 fetcher 模組(22 個新聞來源 + 商工登記 + 企業官網)
├── analysis/             # 產業歸類(classifier)、摘要與策略生成(summarizer)
├── app/                  # 網頁介面(FastAPI + 單頁前端)
├── report/               # Word 報告產生器(python-docx)
├── scheduler_setup/      # 每週一 12:00 排程設定腳本(Windows/Linux/macOS)
├── company_sites.json    # 企業官網新聞稿頁面登錄表
├── data/                 # SQLite 資料庫(自動建立)
├── reports/              # Word 報告輸出資料夾
└── logs/                 # 執行紀錄
```

## 安裝

```bash
pip install -r requirements.txt
```

需 Python 3.10+(開發環境為 3.13)。

## 使用方式

### 1. 抓取資料

```bash
python main.py fetch                          # 全部來源
python main.py fetch --sources cna,ltn        # 指定來源(模組名見 config.py)
```

增量更新:以原文連結去重,重複執行不會產生重複資料。單一來源失敗不影響其他來源,狀態記錄於資料庫 `fetch_log`。

### 2. 網頁介面

```bash
python main.py serve --port 8000
```

開啟 http://127.0.0.1:8000:

- **期間選擇**:YTD、近 7/30/90 天、自訂起訖日期
- **公司搜尋**:輸入公司名稱或 8 碼統編,彙整期間內相關報導、官網公告與商工登記資料
- **產業瀏覽**:依 11 大產業分類篩選瀏覽
- **匯出 Word 報告**:一鍵下載;若公司欄位有值則產出公司情報報告

### 3. 產出報告(命令列)

```bash
python main.py report --days 30                          # 近 30 天
python main.py report --start 2026-01-01 --end 2026-06-30  # 自訂期間
```

### 4. 每週自動更新

見 [scheduler_setup/README.md](scheduler_setup/README.md)。Windows 一鍵設定:

```bash
powershell -ExecutionPolicy Bypass -File scheduler_setup\setup_windows.ps1
```

每週一 12:00 自動:抓取新資料 → 更新資料庫 → 產出上週週報至 `reports/`。

## 自動通知

每次雲端更新後,系統自動檢查並於必要時**開 GitHub Issue**(GitHub 會寄 email 給關注者):

- **負面聲量警示**:觀察名單公司首次出現疑似負面報導、或篇數較上次通知倍增(≥3 篇)
- **來源健康**:應可抓取之來源連續 3 次失敗(同一來源 7 天內不重複通知)

通知狀態記錄於 `data/alert_state.json`;若要收到 email,請確認 GitHub 帳號有 Watch 本 repo(Participating and @mentions 即可,Issue 內會 @ 擁有者)。

## 產業分類

11 大類對照行政院主計總處[「行業統計分類」](https://www.stat.gov.tw/standardindustrialclassification.aspx?n=3144&sms=0&rid=8)(對照代碼見 `config.py`),以關鍵字比對自動歸類;無法歸類的文章保留於資料庫但不列入產業摘要。關鍵字表可於 `config.py` 之 `INDUSTRIES` 自行增修。

## 資料來源與限制

| 類型 | 來源 | 方式 | 狀態(2026-08 實測) |
|---|---|---|---|
| 綜合新聞 | 中央社、ETtoday、自由時報、壹蘋 | RSS | ✅ 可自動抓取 |
| 綜合新聞 | Yahoo奇摩 | RSS+出處還原 | ✅ 新文章解析文章頁 JSON-LD 還原原始媒體,標為「媒體名(Yahoo轉載)」 |
| 綜合新聞 | 中時 | — | ❌ 官網 robots.txt 不允許;轉載至 Yahoo 之內容可經出處還原取得 |
| 綜合新聞 | NOWnews、TVBS、三立 | — | ❌ 官網無公開 RSS;轉載至 Yahoo 之內容可經出處還原取得 |
| 綜合新聞 | 風傳媒 | — | ❌ RSS 為會員限定,無法自動抓取 |
| 綜合新聞 | 聯合新聞網 | — | ❌ RSS 服務回傳空白項目;財經內容由經濟日報涵蓋 |
| 綜合新聞 | LINE Today | — | ❌ 無公開 RSS 且限制爬取,僅提供入口連結 |
| 財經專業 | Anue鉅亨、經濟日報 | RSS | ✅ 可自動抓取(經濟日報部分訂閱制,僅公開標題+摘要) |
| 財經專業 | 工商時報 | — | ❌ robots.txt 不允許程式抓取 |
| 財經專業 | MoneyDJ | — | ❌ 網站憑證鏈異常,暫無法抓取 |
| 深度雜誌 | 商業周刊、遠見 | RSS | ✅ 可自動抓取(付費牆內容僅公開標題+摘要) |
| 深度雜誌 | 今周刊、天下 | — | ❌ 無公開 RSS / robots.txt 不允許;轉載至 Yahoo 之內容可經出處還原取得 |
| 科技新創 | 數位時代、科技新報 | — | ❌ 無公開 RSS / robots.txt 不允許;轉載至 Yahoo 之內容可經出處還原取得 |
| 官方公告 | 證交所重大訊息(OpenAPI) | API | ✅ 上市公司每日重大訊息(含台積電、華碩官方公告),法定揭露管道 |
| 企業官網 | 華碩(company_sites.json 登錄制) | HTML | ✅ 可自動抓取;台積電新聞室 robots.txt 不允許,官方訊息由證交所重大訊息涵蓋 |
| 公司登記 | 經濟部 GCIS 開放資料 API | API | 平臺憑證鏈異常時預設回退為[商工登記人工查詢連結](https://findbiz.nat.gov.tw/fts/query/QueryBar/queryInit.do)(網頁版含驗證碼,不做自動化);詳見 `config.py` 之 `GCIS_ALLOW_INSECURE_SSL` 說明 |
| 企業官網 | company_sites.json 登錄制 | HTML/RSS | 需逐家登錄新聞稿頁面網址;未登錄公司回報限制訊息 |

爬取行為:遵守 robots.txt、每請求間隔 2 秒、失敗重試 2 次。

## 可溯源原則

- 每筆資料保留:標題、摘要、來源媒體、發布日期、原文連結、產業分類
- 報告中每一條摘要均附出處「(媒體,日期,連結)」;附錄含引用來源總表
- 「建議策略」為規則式主題統計(關鍵詞頻率)產生之觀察,報告中標明「AI 分析,僅供參考」,且每項附代表性報導出處
- 期間內無資料的產業,明確標示「資料不足」,不產生無出處內容

## 測試

```bash
python tests\test_report_content.py   # 驗證報告章節結構與出處標記
python tests\test_findbiz.py          # 商工登記 API 煙霧測試
```
