#!/usr/bin/env bash
# 台灣產業趨勢監測系統 — cron 設定(Linux/macOS,每週一 12:00 自動更新)
# 執行:bash setup_cron.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3 || command -v python)"
CRON_LINE="0 12 * * 1 cd ${PROJECT_DIR} && ${PYTHON_BIN} main.py weekly >> ${PROJECT_DIR}/logs/scheduler.log 2>&1"

# 移除既有同專案排程後重新加入,避免重複
( crontab -l 2>/dev/null | grep -v "main.py weekly" ; echo "${CRON_LINE}" ) | crontab -

echo "cron 排程已設定:每週一 12:00 執行 main.py weekly"
echo "報告輸出資料夾:${PROJECT_DIR}/reports"
echo "執行紀錄:${PROJECT_DIR}/logs/run.log 與 logs/scheduler.log"
crontab -l | grep "main.py weekly"
