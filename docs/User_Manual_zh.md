# 操作手冊 — Illumio Rule Scheduler

🌐 [English](User_Manual_en.md) | [繁體中文](User_Manual_zh.md)

---

## 目錄

1. [前置需求](#1-前置需求)
2. [設定](#2-設定)
3. [啟動應用程式](#3-啟動應用程式)
4. [Web GUI 操作流程](#4-web-gui-操作流程)
5. [CLI 操作流程](#5-cli-操作流程)
6. [部署為系統服務](#6-部署為系統服務)
7. [疑難排解](#7-疑難排解)

---

## 1. 前置需求

| 需求 | 詳細 |
|------|------|
| Python | 3.7 或更高版本 |
| Flask | 選用 — 僅 Web GUI 模式需要（`pip install flask`） |
| PCE API Key | 必須具有 **Ruleset Provisioner** 或 **Global Organization Owner** 角色 |
| 網路 | 可 HTTPS 存取 PCE（預設 Port 8443） |

### 建立 API Key

1. 登入 Illumio PCE 網頁主控台。
2. 前往 **Settings → API Keys → Add**。
3. 記下 **API Key ID** 和 **API Secret**（Secret 只顯示一次）。
4. 確保 Key 至少具有 **Ruleset Provisioner** 權限。

---

## 2. 設定

### 快速設定

```bash
cp config.json.example config.json
```

編輯 `config.json` 填入 PCE 資訊：

```json
{
    "pce_url": "https://your-pce.example.com:8443",
    "org_id": "1",
    "api_key": "api_xxxxxxxxxxxxxxxx",
    "api_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "ssl_verify": true,
    "lang": "zh"
}
```

### 設定欄位說明

| 欄位 | 必填 | 說明 |
|------|------|------|
| `pce_url` | ✅ | PCE 完整網址含 Port（例如 `https://pce.company.com:8443`） |
| `org_id` | ✅ | 組織 ID（通常為 `1`） |
| `api_key` | ✅ | PCE 中的 API Key ID |
| `api_secret` | ✅ | API Secret（以明文儲存，請注意檔案權限） |
| `ssl_verify` | ❌ | 自簽憑證時設為 `false`（預設：`true`） |
| `check_interval_seconds` | ❌ | 排程引擎檢查間隔秒數（預設：`300` = 5 分鐘） |
| `lang` | ❌ | 介面語言：`"en"` (English) 或 `"zh"` (繁體中文) |
| `alert_email` | ❌ | 排程觸發通知的 Email |
| `smtp_host` | ❌ | SMTP 伺服器主機名 |
| `smtp_port` | ❌ | SMTP 伺服器 Port（預設：`587`） |
| `smtp_auth` | ❌ | 啟用 SMTP 驗證（`true`/`false`） |

### 環境變數

| 變數 | 說明 |
|------|------|
| `ILLUMIO_PORT` | 覆蓋預設 Web GUI Port（預設：`5002`） |
| `ILLUMIO_CHECK_INTERVAL` | 覆蓋排程檢查間隔秒數（若 `config.json` 未設定 `check_interval_seconds` 時的備用值） |

---

## 3. 啟動應用程式

### Web GUI 模式

```bash
python illumio_scheduler.py --gui
python illumio_scheduler.py --gui --port 8080   # 自訂 Port
```

自動開啟瀏覽器至 `http://localhost:5002`。

### CLI 模式

```bash
python illumio_scheduler.py
```

啟動互動式終端選單。

### Daemon 模式

```bash
python illumio_scheduler.py --monitor
```

在前景持續運行排程引擎，預設每 300 秒（5 分鐘）檢查一次。可透過 `config.json` 中的 `check_interval_seconds` 調整。

---

## 4. Web GUI 操作流程

### 分頁 1：瀏覽與新增排程

1. **瀏覽規則集** — 左側面板列出所有 PCE 規則集，可使用搜尋列篩選。
2. **檢視規則** — 點擊規則集展開右側面板中的子規則。
3. **新增排程** — 點擊規則或規則集列，再按 **「+ 新增排程」** 開啟排程設定視窗。

#### 建立循環排程

1. 選擇 **排程類型：循環排程**。
2. 選擇 **動作**：
   - *時段內啟用* — 時段內啟用規則，時段外停用。
   - *時段內停用* — 時段內停用規則，時段外啟用。
3. 輸入 **星期**（逗號分隔）：`Monday,Tuesday,Wednesday,Thursday,Friday`
4. 輸入 **開始時間** 和 **結束時間**：例如 `08:00` 和 `18:00`
5. 點擊 **儲存**。

#### 建立一次性到期

1. 選擇 **排程類型：一次性到期**。
2. 輸入 **到期日期時間**：例如 `2025-12-31 23:59`
3. 點擊 **儲存**。

### 分頁 2：已排程任務

檢視所有已設定的排程，可以：
- 查看目前啟用/停用狀態
- 刪除排程（選取列 → 按 **刪除選取**）

### 分頁 3：執行引擎

按 **「立即執行」** 手動觸發排程引擎。日誌面板顯示執行結果。

### 分頁 4：設定

更新 PCE 連線和語言偏好，無需手動編輯 `config.json`。

---

## 5. CLI 操作流程

CLI 呈現編號選單：

```
========== Illumio Rule Scheduler ==========
1. 瀏覽與管理規則集
2. 檢視已排程任務
3. 立即執行排程檢查
4. 設定
5. 結束
=============================================
```

### 瀏覽與管理

1. 選擇 `1` 列出所有規則集。
2. 輸入規則集 ID 檢視其規則。
3. 選擇規則後選擇動作：
   - 新增循環排程
   - 新增一次性到期
   - 移除排程

### 執行檢查

選擇 `3` 立即運行排程引擎，查看結果。

---

## 6. 部署為系統服務

### Windows (NSSM)

使用提供的 PowerShell 腳本：

```powershell
.\deploy\deploy_windows.ps1
```

使用 [NSSM](https://nssm.cc/) 安裝為 Windows 服務。

### Linux (systemd)

1. 複製服務檔案：
   ```bash
   sudo cp deploy/illumio-scheduler.service /etc/systemd/system/
   ```
2. 編輯服務檔案設定正確路徑。
3. 啟用並啟動：
   ```bash
   sudo systemctl enable illumio-scheduler
   sudo systemctl start illumio-scheduler
   ```

---

## 7. 疑難排解

### 無法連線到 PCE

- 確認 `pce_url` 包含 Port（例如：`:8443`）。
- 自簽憑證需設定 `"ssl_verify": false`。
- 確認 API Key 尚未過期。

### 規則沒有被切換

- 確認 API Key 有 **Ruleset Provisioner** 或更高權限。
- 確認排程正確（到 **已排程任務** 分頁檢查）。
- 手動執行引擎查看詳細日誌。

### GET 回傳的規則集比預期少

- 工具使用 `max_results=10000` 來超越 PCE 預設 500 筆限制。
- 如果有超過 10,000 個規則集，請聯絡 PCE 管理員。

### Web GUI 無法啟動

- 確認已安裝 Flask：`pip install flask`
- 檢查 Port 是否被佔用：試試 `--port 8080`

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [功能總覽](README_zh.md) | 程式介紹與功能 |
| [程式架構](Architecture_zh.md) | 程式碼結構與擴展指南 |
| [API 教學手冊](API_Cookbook_zh.md) | Python 直接呼叫 Illumio API 範例 |
