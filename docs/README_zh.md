# Illumio Rule Scheduler — 功能總覽與介紹

🌐 [English](README_en.md) | [繁體中文](README_zh.md)

---

## 什麼是 Illumio Rule Scheduler？

Illumio Rule Scheduler 是一個基於 Python 的自動化工具，用來排程啟用和停用 [Illumio Policy Compute Engine (PCE)](https://www.illumio.com/) 中的**安全策略規則 (Rule)** 和**規則集 (RuleSet)**。

### 為什麼需要它？

Illumio PCE 原生不支援基於時間的規則排程。這個工具填補了這個缺口：

- **循環排程 (Recurring)** — 在營業時間自動啟用規則（例如：週一至週五 08:00–18:00），並在營業時間外自動停用。
- **一次性到期 (One-Time Expiration)** — 設定規則在特定日期/時間後自動停用（例如：臨時防火牆例外）。

### 運作原理

1. 透過 **Web GUI**、**CLI** 或直接編輯 JSON 資料庫來設定排程。
2. 工具會將排程標籤附加到 PCE 中規則的 `description` 欄位（例如：`[📅 循環: Mon-Fri 08:00-18:00 時段內啟用]`）。
3. 背景監控程式定期檢查當前時間與所有已設定的排程。
4. 當排程觸發時，工具呼叫 Illumio REST API 切換規則的 `enabled` 狀態並發布變更。

### 核心功能

| 功能 | 說明 |
|------|------|
| **三種運行模式** | Web GUI（Flask）、CLI（互動式終端）、Daemon（背景服務） |
| **循環排程** | 設定星期和時間窗口，自動啟用/停用 |
| **一次性到期** | 設定規則在特定日期時間到期 |
| **依賴感知發布** | 自動探索並發布相依物件 |
| **雙語介面** | 英文和繁體中文 |
| **明暗主題** | Web GUI 支援主題切換 |
| **零外部依賴** | 核心引擎僅使用 Python 標準函式庫 |
| **服務部署** | 提供 Windows (NSSM) 和 Linux (systemd) 的部署腳本 |

### 支援的排程類型

#### 循環排程 (Recurring)
設定規則在特定星期和時間窗口內自動啟用或停用。

- **動作：時段內啟用 (ENABLE in window)** — 在時段內啟用規則，時段外停用。
- **動作：時段內停用 (DISABLE in window)** — 在時段內停用規則，時段外啟用。

#### 一次性到期 (One-Time Expiration)
規則在到期時間自動停用，排程隨即移除。

---

## 運行模式

### 1. Web GUI
基於 Flask 的單頁應用程式，響應式設計。

```bash
python illumio_scheduler.py --gui --port 5002
```

### 2. CLI（互動式）
終端互動介面，可瀏覽規則集和管理排程。

```bash
python illumio_scheduler.py
```

### 3. Daemon（背景監控）
持續運行排程引擎，預設每 300 秒（5 分鐘）檢查一次。

```bash
python illumio_scheduler.py --monitor
```

---

## 系統需求

- **Python 3.7+**
- **Flask**（選用，僅 Web GUI 模式需要）：`pip install flask`
- **Illumio PCE**，需要具有 **Ruleset Provisioner** 或 **Global Organization Owner** 權限的 API Key

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [操作手冊](User_Manual_zh.md) | 逐步操作指南 |
| [程式架構](Architecture_zh.md) | 程式碼結構、類別設計、擴展指南 |
| [API 教學手冊](API_Cookbook_zh.md) | Python 直接呼叫 Illumio API 的範例 |
