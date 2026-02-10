# 🕒 Illumio Rule Scheduler (CLI)

![Python](https://img.shields.io/badge/Python-3.6%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux-orange?logo=linux&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-green)

這是一個針對 **Illumio Core (PCE)** 設計的進階自動化排程工具。它允許管理者透過互動式 CLI 介面，設定特定「規則 (Rule)」或「規則集 (RuleSet)」的生效時段，並透過背景服務自動執行狀態切換與發布 (Provisioning)。  
<img width="630" height="648" alt="image" src="https://github.com/user-attachments/assets/e67c0d43-b8dc-4aee-afd0-a849b9019138" />  


---

## ✨ 核心功能

* **📅 自動化排程**
    * **每週循環 (Recurring)**：指定星期與時段（例如：每週一至週五 08:00-18:00 啟動）。
    * **自動過期 (Auto-Expire)**：設定失效時間，時間到後自動關閉規則並**刪除排程**，實現「用完即丟」的臨時權限管理。

* **👁️ 視覺化雙重指標**
    * `★` (黃色)：表示**規則集本身**已被排程。
    * `●` (青色)：表示規則集無排程，但其**子規則**有排程。
    * **即時同步 (Live Sync)**：列表時即時檢查 PCE 狀態，若規則在 Web UI 被刪除，CLI 會標示 `[已刪除]`。

* **📝 Note 自動整合**
    * 自動將排程狀態（如 `[📅 排程: 每天 08:00 啟動]`）寫入 Illumio 規則的 **Description** 欄位。
    * 刪除排程時，自動清除該標記，保持 Description 整潔。

* **⚙️ 架構**
    * **背景監控**：支援 Linux Systemd Service，開機自動在背景執行檢查。
    * **混合搜尋**：支援 ID 直達、關鍵字模糊搜尋、分頁瀏覽。
    * **ANSI 色彩介面**：支援紅綠燈號狀態顯示 (`✔ ON` / `✖ OFF`)。

---

## 🛠️ 環境準備與安裝

基於 Python 3 開發，依賴 `requests` 模組。建議安裝於 `/opt/illumio_scheduler`。

### 第一步：安裝 Python 與相依套件

請依照您的作業系統選擇指令：

**針對 Red Hat Enterprise Linux (RHEL) 8/9, Rocky Linux, AlmaLinux**

1. 更新系統並安裝 Python 3 與 Pip
sudo dnf update -y sudo dnf install python3 python3-pip -y

2. 建立專案目錄
sudo mkdir -p /opt/illumio_scheduler cd /opt/illumio_scheduler

3. 建立虛擬環境 (強烈建議)
python3 -m venv venv source venv/bin/activate

4. 安裝依賴
pip install requests


> **注意**：若您將腳本放在 `/root`，Systemd 服務可能會被 SELinux 阻擋。強烈建議放在 `/opt/` 下。

**針對 Ubuntu 20.04 / 22.04 / 24.04, Debian**

1. 更新並安裝 Python 3
sudo apt update sudo apt install python3 python3-pip python3-venv -y

2. 建立專案目錄
sudo mkdir -p /opt/illumio_scheduler cd /opt/illumio_scheduler

3. 建立虛擬環境
python3 -m venv venv source venv/bin/activate

4. 安裝依賴
pip install requests


### 第二步：部署腳本

將 `illumio_scheduler.py` 上傳至 `/opt/illumio_scheduler` 目錄並賦予執行權限：

chmod +x illumio_scheduler.py


---

## 🚀 使用說明 (互動模式)

直接執行腳本進入管理選單：

若使用了 venv，請先 activate，或直接呼叫 venv 中的 python
/opt/illumio_scheduler/venv/bin/python3 illumio_scheduler.py


### 功能選單詳解

* **0. 設定 API**
    初次使用必填。輸入 PCE URL、Org ID、API Key 與 Secret (加密儲存於 `config.json`)。

* **1. 瀏覽與新增**
    支援 **ID 直達** (如 `272`) 或 **關鍵字搜尋** (如 `vmware`)。亦可直接按 Enter 瀏覽全部。

* **2. 列表 (Grouped)**
    以樹狀結構顯示目前的排程，並標示 `★` (母集排程) 與 `●` (子集排程) 狀態。

* **3. 刪除排程**
    輸入 ID 移除排程控管。程式會自動將 PCE 上 Description 欄位的註記清除。

* **4. 立即檢查**
    手動觸發一次邏輯檢查 (Dry Run)，用於測試設定是否正確。

---

## ⚙️ 背景服務設定 (Systemd)

為了讓排程自動運作（即使登出或重開機），請設定 Systemd 服務。

### 1. 建立 Service 檔案

建立 `/etc/systemd/system/illumio-scheduler.service` 檔案：

[Unit] Description=Illumio Rule Auto-Scheduler Service After=network.target

[Service] Type=simple User=root

設定工作目錄 (非常重要，確保能讀取到 config.json)
WorkingDirectory=/opt/illumio_scheduler

指向 venv 中的 python，並加上 --monitor 參數
ExecStart=/opt/illumio_scheduler/venv/bin/python3 illumio_scheduler.py --monitor Restart=always RestartSec=10

[Install] WantedBy=multi-user.target


### 2. 啟動服務

執行以下指令啟用服務：

重新讀取設定
sudo systemctl daemon-reload

啟動服務並設定開機自啟
sudo systemctl enable --now illumio-scheduler

檢查狀態
sudo systemctl status illumio-scheduler


### 3. 查看運作日誌

sudo journalctl -u illumio-scheduler -f


---

## ⚠️ 重要注意事項

1.  **時間同步 (NTP)**
    腳本依賴伺服器的**本地時間** (`datetime.now()`) 進行判斷。請確保 Linux 主機時區與時間正確 (使用 `timedatectl` 檢查)。

2.  **API 權限**
    使用的 API Key 必須具備 **Global Admin** 或該規則集的 **Ruleset Provisioner** 權限，否則無法寫入 Description 或執行發布。

3.  **發布機制 (Provisioning)**
    本工具在變更狀態後會自動觸發 Provision。
    **注意**：Provision 是以 **RuleSet** 為單位。如果該 RuleSet 中有其他「人為修改但尚未發布」的草稿 (Draft)，也會被此工具一併發布出去。建議保持 Draft 乾淨。

4.  **檔案保存**
    * `config.json`: 存放 API 金鑰，請妥善保護。
    * `rule_schedules.json`: 存放排程資料庫，請勿隨意手動修改。
