# 台灣產業趨勢監測系統 — Windows 工作排程器設定(每週一 12:00 自動更新)
# 以系統管理員或一般使用者權限執行皆可(工作以目前使用者身分執行)。
# 執行:powershell -ExecutionPolicy Bypass -File setup_windows.ps1

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python).Source
$TaskName = "IndustryMonitor_Weekly"

# 若已存在同名工作,先刪除再重建
schtasks /Query /TN $TaskName 2>$null
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $TaskName /F
}

# /SC WEEKLY /D MON /ST 12:00 → 每週一 12:00
# 以 cmd /c 包裝以便設定工作目錄與輸出導向
$Action = "cmd /c cd /d `"$ProjectDir`" && `"$Python`" main.py weekly >> `"$ProjectDir\logs\scheduler.log`" 2>&1"

schtasks /Create /TN $TaskName /TR $Action /SC WEEKLY /D MON /ST 12:00 /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "排程建立成功:每週一 12:00 執行 main.py weekly"
    Write-Host "報告輸出資料夾:$ProjectDir\reports"
    Write-Host "執行紀錄:$ProjectDir\logs\run.log 與 logs\scheduler.log"
    Write-Host "手動測試:schtasks /Run /TN $TaskName"
} else {
    Write-Host "排程建立失敗,請確認權限後重試。"
}
