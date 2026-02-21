# Illumio Rule Scheduler

![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-gold?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)


> [English](#english) | [繁體中文](#繁體中文)

---

## English

An automated rule scheduling tool for **Illumio Core (PCE)**. Supports **Web GUI**, **CLI**, and **Daemon** modes. Core engine uses only Python standard library — Flask is the only optional dependency (for Web GUI only).

---

## ✨ Features

| Feature | Description |
|---|---|
| 📅 **Recurring Schedule** | Enable/disable rules on a weekly schedule (supports cross-midnight, e.g. 22:00–06:00) |
| ⏳ **Auto-Expiration** | One-time rules that auto-disable and self-delete after a set time |
| 🖥️ **Web GUI + CLI** | Flask-powered Web GUI (auto-opens browser); ANSI CLI for SSH/terminal |
| 🌐 **i18n Support** | Language toggle between English (default) and Traditional Chinese |
| 👁️ **Visual Indicators** | `PROV` state (ACTIVE/DRAFT), symbols (★ = RS scheduled, ● = Child rule) |
| 🛡️ **Draft Safety** | Prevents scheduling of unprovisioned (draft-only) rules |
| 📝 **Note Integration** | Automatically writes schedule status to Illumio `description` field |
| 🔄 **Dependency-Aware Provisioning** | Discovers and includes all PCE dependencies before provisioning |
| 🛡️ **Zero Core Dependencies** | Core engine and CLI use only Python standard library |

---

## 📁 Project Structure

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py          # Entry point (CLI / GUI / Daemon)
├── src/
│   ├── __init__.py
│   ├── core.py                   # Core engine (API, DB, scheduling logic)
│   ├── cli_ui.py                 # CLI interactive interface
│   ├── gui_ui.py                 # Flask Web GUI (dark theme SPA)
│   └── i18n.py                   # Internationalisation (EN/ZH string tables)
├── deploy/
│   ├── deploy_windows.ps1        # Windows NSSM service deployment
│   └── illumio-scheduler.service # Linux systemd unit file
├── config.json                   # API settings (generated at runtime, git-ignored)
├── rule_schedules.json           # Schedule database (generated at runtime, git-ignored)
└── README.md
```

---

## 🛠️ Installation

**Core requirement**: Python 3.8+

**Web GUI** (optional): `pip install flask`
> CLI mode works without Flask. If Flask is not installed, the `--gui` flag will display install instructions instead.

**Linux / macOS**:
```bash
sudo mkdir -p /opt/illumio_scheduler
cd /opt/illumio_scheduler
# Copy project files here
chmod +x illumio_scheduler.py
pip install flask    # optional, for Web GUI only
```

**Windows**:
1. Install [Python 3](https://www.python.org/downloads/) (check "Add to PATH")
2. Place the project directory anywhere (e.g. `C:\illumio_scheduler`)
3. Optionally: `pip install flask` for Web GUI

---

## 🚀 User Guide

The tool supports three operational modes.

### 1. Web GUI Mode (Recommended)
Launch the Flask-powered Web GUI for a complete visual experience:
```bash
python illumio_scheduler.py --gui --port 5000
```
- **Interface**: Opens a dark-themed single-page application in your default browser.
- **Browse & Add**: Search through your RuleSets. Click a RuleSet to view its rules, select the desired target, and click "Schedule Selected".
- **Schedules Tab**: View, edit, or delete existing schedules. Supports checkbox multi-selection for bulk deletion.
- **Logs & Check**: Manually trigger the schedule engine using "Run Manual Check Now" and view the background execution logs directly in the browser.
- **Settings**: Configure your PCE URL, Org ID, and API credentials securely.

### 2. CLI Mode (For SSH / Terminal)
Designed for environments without desktop access. Run the script without arguments:
```bash
python illumio_scheduler.py
```
**Interactive Main Menu:**

```text
=== Illumio Scheduler ===
0. Settings
1. Schedule Management (Browse/List/Edit/Delete)
2. Run Check Now
3. Open Web GUI
q. Quit
```

- **`0. Settings`**: Access system settings, including API configuration, language switching, SSL verification, and SMTP settings.
- **`1. Schedule Management`**: Opens the unified dashboard.
  - Type `a` to browse and add a new schedule with a paginated wizard.
  - Type `e <ID>` to edit an existing schedule's time window.
  - Type `d <ID>` (or `d 1,2,3`) to delete schedules.
- **`2. Run Check Now`**: Manually execute a schedule check and print the logs to the console.
- **`3. Open Web GUI`**: Switches the running instance into Web GUI mode.

### 3. Daemon Mode (Background Monitoring)
This mode runs continuously in the background to automatically apply your schedules:
```bash
python illumio_scheduler.py --monitor
```
> The engine wakes up (default: every 300 seconds), compares the current time against your database, toggles the rule statuses via the PCE API, provisions the changes, and goes back to sleep.

---

## ⚙️ Deployment Scripts & Mechanics

To ensure schedules trigger reliably over time, the script must run continuously as a background service. We provide two deployment wrappers.

### Windows: NSSM (`deploy_windows.ps1`)

**Mechanics**: Windows requires an executable wrapper to treat a simple Python script as a background Service. We utilize **[NSSM (Non-Sucking Service Manager)](http://nssm.cc/)** to wrap `python illumio_scheduler.py --monitor`. NSSM automatically captures stdout/stderr, redirects it to the Windows Event Log, and guarantees the process is restarted if it crashes.

**Installation**:
1. Download NSSM and extract `nssm.exe`.
2. Run PowerShell as **Administrator**:
   ```powershell
   .\deploy\deploy_windows.ps1 -NssmPath "C:\path\to\nssm.exe"
   ```
3. The script automatically creates a service named `IllumioScheduler`, configures it to start on boot, and launches it immediately.

### Linux: Systemd (`illumio-scheduler.service`)

**Mechanics**: Uses native Linux init daemon integration. The provided `.service` file instructs systemd to execute the script in `--monitor` mode using the system python binary, defines the working directory context, and specifies `Restart=always` to ensure high availability.

**Installation**:
```bash
sudo cp deploy/illumio-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now illumio-scheduler
sudo journalctl -u illumio-scheduler -f
```

---

## 🏗️ Architecture (For Developers)

### Module Overview

| Module | Responsibility |
|---|---|
| `illumio_scheduler.py` | Entry point: routes to CLI (`default`), Web GUI (`--gui`), or Daemon (`--monitor`) |
| `src/core.py` | Core engine: `ConfigManager`, `ScheduleDB`, `PCEClient`, `ScheduleEngine` — zero external deps |
| `src/cli_ui.py` | CLI interactive menu: browse/add/edit/delete schedules, language selector |
| `src/gui_ui.py` | Flask Web GUI: REST API endpoints + embedded HTML/CSS/JS SPA |
| `src/i18n.py` | i18n string tables (EN, ZH). Call `t('key')` to translate |

### Core Classes (`src/core.py`)

| Class | Description |
|---|---|
| `ConfigManager` | Loads/saves `config.json` (PCE URL, org, API key/secret) |
| `ScheduleDB` | JSON-based schedule database (`rule_schedules.json`) |
| `PCEClient` | Illumio PCE REST API client using `urllib.request` (zero deps) |
| `ScheduleEngine` | The scheduling logic: compares current time against schedules, toggles rules |

### Web GUI API Endpoints (`src/gui_ui.py`)

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Serve the SPA HTML page |
| `/api/rulesets` | GET | List all rulesets (supports `?q=keyword` search) |
| `/api/rulesets/<id>` | GET | Get single ruleset with all rules |
| `/api/schedules` | GET | List all configured schedules |
| `/api/schedules` | POST | Create or overwrite a schedule |
| `/api/schedules/<href>` | DELETE | Delete a schedule and clean up notes |
| `/api/check` | POST | Run manual policy check |
| `/api/config` | GET/POST | Get or save API configuration |
| `/api/stop` | POST | Graceful server shutdown |

### PCE API Integration

- **API Version**: v2 (Illumio Core 25.2+)
- **Authentication**: HTTP Basic Auth via `Authorization` header
- **SSL**: Disabled verification (`ssl.CERT_NONE`) for self-signed PCE certificates
- **Provisioning**: Dependency-aware — calls `POST /sec_policy/draft/dependencies` before provisioning to include all required objects

### i18n System (`src/i18n.py`)

```python
from src.i18n import t, set_lang, get_lang

set_lang('zh')        # Switch to Traditional Chinese
set_lang('en')        # Switch to English (default)
print(t('app_title')) # Get translated string
```

To add a new language, add a new key in `_STRINGS` dict (e.g. `'ja'`) with all the same keys as `'en'`.

### Schedule Data Format (`rule_schedules.json`)

```json
{
  "/orgs/1/sec_policy/draft/rule_sets/206": {
    "type": "recurring",
    "name": "K8sNode | Kubernetes",
    "is_ruleset": true,
    "action": "allow",
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "start": "08:00",
    "end": "18:00",
    "detail_rs": "K8sNode | Kubernetes",
    "detail_src": "All",
    "detail_dst": "All",
    "detail_svc": "All",
    "detail_name": "K8sNode | Kubernetes"
  }
}
```

| Field | Description |
|---|---|
| `type` | `recurring` or `one_time` |
| `is_ruleset` | `true` if scheduling the entire RuleSet, `false` for a single rule |
| `action` | `allow` (enable in window) or `block` (disable in window) |
| `days` | Array of day names (e.g. `["Monday", "Friday"]`) |
| `start` / `end` | Time window in `HH:MM` format (supports cross-midnight) |
| `expire_at` | ISO datetime for one-time expiration (e.g. `2025-12-31T23:59`) |

---

## ⚠️ Notes & Troubleshooting

1. **Clock accuracy** — Ensure the host timezone is correct (`timedatectl` / Windows time settings)
2. **API permissions** — The API Key must have **Global Admin** or **Ruleset Provisioner** privileges
3. **Provisioning scope** — Provisioning is per-RuleSet; the tool auto-discovers dependencies to avoid conflicts
4. **Check interval** — Default is 300 seconds; adjust with env var `ILLUMIO_CHECK_INTERVAL=<seconds>`
5. **Security** — API credentials are stored in plaintext in `config.json`; set appropriate directory permissions
6. **Flask not found** — If you see "Flask is required", install with `pip install flask`. CLI works without it.

---

## 📄 License

This project is provided as-is for internal use.

---

<br>

## 繁體中文

**Illumio Core (PCE)** 自動化規則排程工具。支援 **Web GUI**、**CLI** 及 **Daemon** 模式。核心引擎僅使用 Python 標準程式庫，Flask 為唯一的選用依賴（僅 Web GUI 需要）。

---

## ✨ 功能特性

| 功能 | 說明 |
|---|---|
| 📅 **週期排程** | 指定星期與時段自動啟停規則（支援跨午夜，如 22:00–06:00） |
| ⏳ **自動過期** | 設定失效時間，時間到後自動關閉並刪除排程 |
| 🖥️ **Web GUI + CLI** | Flask 驅動的 Web GUI（自動開啟瀏覽器）；SSH 環境使用 CLI 選單 |
| 🌐 **多語系** | 支援語系切換：英文（預設）與繁體中文 |
| 👁️ **視覺指標** | `PROV` 狀態（ACTIVE/DRAFT），符號（★ = 規則集排程，● = 子規則排程） |
| 🛡️ **草稿保護** | 阻擋對未發布（僅存於草稿）的規則進行排程，減少錯誤 |
| 📝 **Note 整合** | 自動將排程狀態寫入 Illumio Description 欄位 |
| 🔄 **依賴感知發布** | 發布前自動探索 PCE 依賴項，避免因缺少依賴而失敗 |
| 🛡️ **零核心依賴** | 核心引擎與 CLI 僅使用 Python 標準程式庫 |

---

## 📁 專案結構

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py          # 程式進入點 (CLI / GUI / Daemon)
├── src/
│   ├── __init__.py
│   ├── core.py                   # 核心引擎（API, DB, 排程邏輯）
│   ├── cli_ui.py                 # CLI 互動介面
│   ├── gui_ui.py                 # Flask Web GUI（深色主題 SPA）
│   └── i18n.py                   # 國際化（EN/ZH 字串表）
├── deploy/
│   ├── deploy_windows.ps1        # Windows NSSM 服務部署腳本
│   └── illumio-scheduler.service # Linux systemd unit 檔案
├── config.json                   # API 設定（執行時產生，已加入 .gitignore）
├── rule_schedules.json           # 排程資料庫（執行時產生，已加入 .gitignore）
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
1. 安裝 [Python 3](https://www.python.org/downloads/)（勾選「Add to PATH」）
2. 將專案目錄放至任意位置（如 `C:\illumio_scheduler`）
3. 選用：`pip install flask` 安裝 Web GUI

---

## 🚀 使用指南 (User Guide)

本工具支援三種執行模式，以適應不同的操作環境。

### 1. Web GUI 模式（推薦桌面環境）
開啟由 Flask 驅動的網頁圖形介面，獲得最完整的視覺體驗：
```bash
python illumio_scheduler.py --gui --port 5000
```
- **介面**：自動在預設瀏覽器開啟深色主題的單頁應用程式 (SPA)。
- **Browse & Add (瀏覽與新增)**：搜尋並檢視您的規則集 (RuleSets)。點擊規則集以查看內部規則，選定目標後按下「Schedule Selected」即可設定排程。
- **Schedules (排程管理)**：檢視、修改或刪除已設定的排程。支援勾選多筆排程進行批次刪除。
- **Logs & Check (日誌與手動檢查)**：透過「Run Manual Check Now」按鈕可手動觸發排程引擎，並直接在瀏覽器中觀看背景執行的詳細日誌。
- **Settings (設定)**：安全地設定您的 PCE URL、Org ID 以及 API 憑證。

### 2. CLI 模式（推薦 SSH / 終端機）
專為無桌面 (GUI) 環境設計。直接執行腳本即可進入互動式選單：
```bash
python illumio_scheduler.py
```
**互動式主選單：**

```text
=== Illumio Scheduler ===
0. Settings
1. Schedule Management (Browse/List/Edit/Delete)
2. Run Check Now
3. Open Web GUI
q. Quit
```

- **`0. Settings`**：進入系統設定，包含 API 連線、語系切換、SSL 憑證驗證與 SMTP 伺服器設定。
- **`1. Schedule Management (排程管理)`**：開啟整合式控制面板。
  - 輸入 `a` 以分頁導覽模式瀏覽並新增排程。
  - 輸入 `e <ID>` 修改現有排程的時間區間。
  - 輸入 `d <ID>`（或 `d 1,2,3`）刪除排程。
- **`2. Run Check Now (立即檢查)`**：手動執行一次排程檢查，並將日誌輸出至終端機。
- **`3. Open Web GUI (開啟 Web GUI)`**：將目前的執行實例切換為 Web GUI 模式。

### 3. Daemon 模式（背景監控）
此模式會在背景持續運行，確保您的排程時間一到就會自動生效：
```bash
python illumio_scheduler.py --monitor
```
> 引擎會定時喚醒（預設：每 300 秒），比對目前時間與資料庫中的排程設定，透過 PCE API 切換規則啟用狀態並自動發布，接著繼續休眠。

---

## ⚙️ 部署腳本與原理解析

為了確保排程能隨著時間精準觸發，腳本必須作為背景服務 (Background Service) 持續運行。我們針對主流作業系統提供了相對應的部署解決方案。

### Windows: NSSM 封裝 (`deploy_windows.ps1`)

**原理解析**：Windows 系統需要透過特製的封裝程式才能將一般的 Python 腳本當作「Windows 服務」執行。我們利用 **[NSSM (Non-Sucking Service Manager)](http://nssm.cc/)** 來封裝 `python illumio_scheduler.py --monitor`。NSSM 會自動攔截腳本的標準輸出/錯誤 (stdout/stderr) 並將其導向 Windows 事件檢視器 (Event Log)，同時保證程式崩潰時會自動重新啟動。

**部署步驟**：
1. 下載 NSSM 並將 `nssm.exe` 解壓縮至任意安全目錄。
2. 以 **系統管理員** 身份開啟 PowerShell 並執行：
   ```powershell
   .\deploy\deploy_windows.ps1 -NssmPath "C:\path\to\nssm.exe"
   ```
3. 腳本會自動建立一個名為 `IllumioScheduler` 的服務，設定為開機自動延遲啟動，並立即啟動它。

### Linux: Systemd 守護行程 (`illumio-scheduler.service`)

**原理解析**：利用 Linux 原生的系統初始化與守護進程管理工具 `systemd`。提供的 `.service` unit 檔案明確指示了以 `--monitor` 模式啟動腳本、指定工作目錄 (Working Directory)，並設定 `Restart=always`，確保服務具備高可用性，即便因為意外中止也會立刻被系統重新拉起。

**部署步驟**：
```bash
sudo cp deploy/illumio-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now illumio-scheduler
sudo journalctl -u illumio-scheduler -f
```

---

## 🏗️ 架構說明（開發者參考）

### 模組總覽

| 模組 | 職責 |
|---|---|
| `illumio_scheduler.py` | 程式進入點：路由至 CLI（預設）、Web GUI（`--gui`）、Daemon（`--monitor`） |
| `src/core.py` | 核心引擎：`ConfigManager`、`ScheduleDB`、`PCEClient`、`ScheduleEngine` — 零外部依賴 |
| `src/cli_ui.py` | CLI 互動選單：瀏覽/新增/修改/刪除排程、語系選擇 |
| `src/gui_ui.py` | Flask Web GUI：REST API 端點 + 內嵌 HTML/CSS/JS SPA |
| `src/i18n.py` | 國際化字串表（EN、ZH）。使用 `t('key')` 取得翻譯 |

### 核心類別（`src/core.py`）

| 類別 | 說明 |
|---|---|
| `ConfigManager` | 載入/儲存 `config.json`（PCE URL、Org ID、API Key/Secret） |
| `ScheduleDB` | JSON 格式的排程資料庫（`rule_schedules.json`） |
| `PCEClient` | Illumio PCE REST API 客戶端，使用 `urllib.request`（零依賴） |
| `ScheduleEngine` | 排程邏輯引擎：比對目前時間與排程設定，切換規則啟停狀態 |

### Web GUI API 端點（`src/gui_ui.py`）

| 路由 | 方法 | 用途 |
|---|---|---|
| `/` | GET | 提供 SPA HTML 頁面 |
| `/api/rulesets` | GET | 列出所有規則集（支援 `?q=關鍵字` 搜尋） |
| `/api/rulesets/<id>` | GET | 取得單一規則集及其規則 |
| `/api/schedules` | GET | 列出所有已設定的排程 |
| `/api/schedules` | POST | 新增或覆寫排程 |
| `/api/schedules/<href>` | DELETE | 刪除排程並清除 Note |
| `/api/check` | POST | 手動執行排程檢查 |
| `/api/config` | GET/POST | 取得或儲存 API 設定 |
| `/api/stop` | POST | 優雅關閉伺服器 |

### PCE API 整合

- **API 版本**：v2（Illumio Core 25.2+）
- **驗證方式**：HTTP Basic Auth 透過 `Authorization` 標頭
- **SSL**：停用憑證驗證（`ssl.CERT_NONE`）以相容自簽憑證
- **發布機制**：依賴感知 — 發布前呼叫 `POST /sec_policy/draft/dependencies` 探索所有必要依賴項

### 國際化系統（`src/i18n.py`）

```python
from src.i18n import t, set_lang, get_lang

set_lang('zh')        # 切換至繁體中文
set_lang('en')        # 切換至英文（預設）
print(t('app_title')) # 取得翻譯後的字串
```

新增語系：在 `_STRINGS` 字典中新增語系代碼（如 `'ja'`），填入與 `'en'` 相同的所有 key。

### 排程資料格式（`rule_schedules.json`）

```json
{
  "/orgs/1/sec_policy/draft/rule_sets/206": {
    "type": "recurring",
    "name": "K8sNode | Kubernetes",
    "is_ruleset": true,
    "action": "allow",
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "start": "08:00",
    "end": "18:00",
    "detail_rs": "K8sNode | Kubernetes",
    "detail_src": "All",
    "detail_dst": "All",
    "detail_svc": "All",
    "detail_name": "K8sNode | Kubernetes"
  }
}
```

| 欄位 | 說明 |
|---|---|
| `type` | `recurring`（週期排程）或 `one_time`（一次性過期） |
| `is_ruleset` | `true` 排程整個規則集，`false` 排程單條規則 |
| `action` | `allow`（時段內啟動）或 `block`（時段內關閉） |
| `days` | 星期名稱陣列（如 `["Monday", "Friday"]`） |
| `start` / `end` | 時間窗口，格式 `HH:MM`（支援跨午夜） |
| `expire_at` | 一次性過期的 ISO 日期時間（如 `2025-12-31T23:59`） |

---

## ⚠️ 注意事項與疑難排解

1. **時鐘精確度** — 確認主機時區正確（`timedatectl` / Windows 時間設定）
2. **API 權限** — API Key 須具備 **Global Admin** 或 **Ruleset Provisioner** 權限
3. **發布範圍** — 本工具會自動探索依賴項，避免因缺少依賴而發布失敗
4. **檢查間隔** — 預設 300 秒，可透過環境變數 `ILLUMIO_CHECK_INTERVAL=<秒>` 調整
5. **安全性** — API 憑證以明文存於 `config.json`，請設定適當的目錄權限
6. **找不到 Flask** — 若顯示 "Flask is required"，請安裝：`pip install flask`。CLI 不需要 Flask。

---

## 📄 License

本專案為內部使用，按原樣提供。
