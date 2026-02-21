# Illumio Rule Scheduler (v4.2.0)

![Version](https://img.shields.io/badge/Version-v4.2.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-gold?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)

> [English](README.md) | [繁體中文](README.zh-TW.md)

---

針對 **Illumio Core (PCE)** 設計的自動化排程工具。支援 **GUI 圖形介面**與 **CLI 命令列**雙模式，**零外部依賴**（僅使用 Python 標準庫），可直接部署於任何安裝了 Python 3.8+ 的環境。

---

## ✨ 核心功能

| 功能 | 說明 |
|---|---|
| 📅 **週期排程** | 指定星期與時段自動啟停規則（支援跨午夜，如 22:00–06:00） |
| ⏳ **自動過期** | 設定失效時間，時間到後自動關閉並刪除排程 |
| 🖥️ **Web GUI + CLI** | Flask 驅動的 Web GUI（自動開啟瀏覽器）；SSH 環境使用 CLI 選單 |
| 👁️ **雙重指標** | ★ = 規則集排程，● = 子規則排程 |
| 📝 **Note 整合** | 自動將排程狀態寫入 Illumio Description 欄位 |
| 🔄 **即時同步** | 列表時即時檢查 PCE 狀態 |
| 🛡️ **零依賴** | 不需要 `pip install` 任何套件，開箱即用 |

---

## 📁 專案結構

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py      # 入口點（CLI / GUI / Daemon 路由）
├── src/
│   ├── __init__.py
│   ├── core.py               # 核心引擎（API, DB, 排程邏輯）
│   ├── cli_ui.py             # CLI 互動介面
│   └── gui_ui.py             # Flask Web GUI（深色主題 SPA）
├── deploy/
│   ├── deploy_windows.ps1    # Windows NSSM 服務部署腳本
│   └── illumio-scheduler.service  # Linux systemd unit
├── config.json               # API 設定（執行時產生）
├── rule_schedules.json       # 排程資料庫（執行時產生）
└── README.md
```

---

## 🛠️ 安裝

**基本需求**：Python 3.8+

**Web GUI**（選用）：`pip install flask`
> CLI 模式不需要 Flask。若未安裝 Flask，使用 `--gui` 時會顯示安裝指令。

**Linux / macOS**：
```bash
sudo mkdir -p /opt/illumio_scheduler
cd /opt/illumio_scheduler
# 將專案檔案複製至此目錄
chmod +x illumio_scheduler.py
pip install flask    # 選用，僅 Web GUI 需要
```

**Windows**：
1. 安裝 [Python 3](https://www.python.org/downloads/)（勾選 "Add to PATH"）
2. 將專案目錄放至任意位置（如 `C:\illumio_scheduler`）

---

## 🚀 使用方式

### GUI 圖形介面（桌面環境推薦）
```bash
python illumio_scheduler.py --gui
```

### CLI 互動模式（SSH / 終端機推薦）
```bash
python illumio_scheduler.py
```
> CLI 選單中也可以按 `5` 直接啟動 GUI。

### Daemon 背景模式
```bash
python illumio_scheduler.py --monitor
```

---

## ⚙️ 背景服務部署

### Windows（推薦 NSSM）

1. 下載 [NSSM](http://nssm.cc/download)
2. 以**系統管理員**身分執行：
   ```powershell
   .\deploy\deploy_windows.ps1 -NssmPath "C:\path\to\nssm.exe"
   ```
3. 服務自動安裝並啟動（名稱：`IllumioScheduler`）

**替代方案：Task Scheduler**
- 建立工作 → 觸發：啟動系統時 → 動作：`python illumio_scheduler.py --monitor`

### Linux（Systemd）

```bash
sudo cp deploy/illumio-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now illumio-scheduler
sudo journalctl -u illumio-scheduler -f
```

---

## ⚠️ 注意事項與疑難排解

1. **時間不準確** — 確保主機時區正確（`timedatectl` / Windows 時間設定）
2. **API 權限** — API Key 需具備 **Global Admin** 或 **Ruleset Provisioner** 權限
3. **Provisioning 連帶** — 發布以 RuleSet 為單位，同一 RuleSet 內未發布的 Draft 會被一併推播
4. **檢查頻率** — 預設 300 秒，可透過環境變數 `ILLUMIO_CHECK_INTERVAL=秒數` 調整
5. **安全性** — API 金鑰以明文儲存於 `config.json`，請設定適當的目錄權限
