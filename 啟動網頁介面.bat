@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在啟動「台灣產業趨勢監測與公司情報系統」網頁介面...
echo 啟動後請用瀏覽器開啟 http://127.0.0.1:8000 (關閉此視窗即停止服務)
start "" http://127.0.0.1:8000
python main.py serve --port 8000
pause
