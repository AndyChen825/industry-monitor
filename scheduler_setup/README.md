# 自動排程設定(每週一 12:00)

排程進入點為 `python main.py weekly`:抓取所有來源新資料(增量,以連結去重)→ 更新 SQLite 資料庫 → 產出「上週(週一至週日)」Word 週報至 `reports/` 資料夾。

## Windows(工作排程器 schtasks)

```powershell
powershell -ExecutionPolicy Bypass -File scheduler_setup\setup_windows.ps1
```

- 建立名為 `IndustryMonitor_Weekly` 的排程工作,每週一 12:00 執行
- 手動測試:`schtasks /Run /TN IndustryMonitor_Weekly`
- 移除:`schtasks /Delete /TN IndustryMonitor_Weekly /F`
- 注意:電腦於週一 12:00 需為開機狀態;若需喚醒或補跑,請於「工作排程器」GUI 中調整該工作的「設定→若錯過排定的啟動時間,盡快啟動工作」

## Linux / macOS(cron)

```bash
bash scheduler_setup/setup_cron.sh
```

- 加入 crontab:`0 12 * * 1 cd <專案目錄> && python3 main.py weekly >> logs/scheduler.log 2>&1`
- 檢視:`crontab -l`;移除:編輯 `crontab -e` 刪除該行

## 執行紀錄與失敗處理

- 每次執行寫入 `logs/run.log`(程式層)與 `logs/scheduler.log`(排程層 stdout/stderr)
- 每個來源抓取結果(ok/error、新增筆數、錯誤訊息)記錄於資料庫 `fetch_log` 資料表
- 單一來源失敗不影響整體;失敗來源會在當週 Word 報告的「資料缺口說明」章節中標示
