Illumio Rule Scheduler (CLI)
這是一個針對 Illumio Core (PCE) 設計的進階自動化排程工具。它允許管理者透過互動式 CLI 介面，設定特定「規則 (Rule)」或「規則集 (RuleSet)」的生效時段，並透過背景服務自動執行狀態切換與發布 (Provisioning)。

✨ 主要功能
自動化排程：

每週循環 (Recurring)：指定星期與時段（例如：每週一至週五 08:00-18:00 啟動）。

自動過期 (Auto-Expire)：設定失效時間，時間到後自動關閉規則並刪除排程。

雙重狀態指標：

★ (黃色)：表示規則集本身已被排程。

● (青色)：表示規則集無排程，但其子規則有排程。

Note 自動整合：自動將排程狀態（如 [📅 排程: 每天 08:00 啟動]）寫入 Illumio 規則的 Description 欄位，並在刪除排程時自動清除。

即時同步 (Live Sync)：列表時即時檢查 PCE 狀態，若規則在 Web UI 被刪除，CLI 會標示 [已刪除]。

視覺化介面：支援 ANSI 色彩顯示、樹狀結構列表、智慧分頁與關鍵字搜尋。

背景監控：支援 Linux Systemd Service，開機自動在背景執行檢查。

🛠️ 環境準備與安裝
本程式基於 Python 3 開發，依賴 requests 模組。

1. 安裝 Python 與相依套件
🔴 Red Hat Enterprise Linux (RHEL) 8/9, Rocky Linux, AlmaLinux
Red Hat 系的系統通常預設有 Python 3，但需要手動安裝 Pip。

Bash
# 1. 更新系統並安裝 Python 3 與 Pip
sudo dnf update -y
sudo dnf install python3 python3-pip -y

# 2. 建立專案目錄 (建議放在 /opt)
sudo mkdir -p /opt/illumio_scheduler
cd /opt/illumio_scheduler

# 3. 建立虛擬環境 (強烈建議，避免污染系統 Python)
python3 -m venv venv
source venv/bin/activate

# 4. 安裝依賴
pip install requests
⚠️ 注意 (RHEL/Rocky 特有問題)：

SELinux: 若您將腳本放在 /root 或特殊目錄，Systemd 服務可能會被 SELinux 阻擋。建議放在 /opt/ 或 /usr/local/ 下。

防火牆: 確保這台 Linux 主機能夠連線至 PCE 的 8443 Port (或其他 API Port)。

🟠 Ubuntu 20.04/22.04/24.04, Debian
Bash
# 1. 更新並安裝 Python 3
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# 2. 建立專案目錄
sudo mkdir -p /opt/illumio_scheduler
cd /opt/illumio_scheduler

# 3. 建立虛擬環境 (Ubuntu 24.04+ 強制要求使用 venv)
python3 -m venv venv
source venv/bin/activate

# 4. 安裝依賴
pip install requests
2. 部署腳本
將 illumio_scheduler.py 上傳至 /opt/illumio_scheduler/ 目錄，並賦予執行權限：

Bash
chmod +x illumio_scheduler.py
🚀 使用說明 (互動模式)
直接執行腳本進入管理選單：

Bash
# 若使用了 venv，請先 activate，或直接呼叫 venv 中的 python
/opt/illumio_scheduler/venv/bin/python3 illumio_scheduler.py
功能選單介紹
0. 設定 API (Settings)：

初次使用請先執行此項。

輸入 PCE URL (如 https://pce.lab.local:8443)、Org ID、API Key 與 Secret。

設定會加密儲存於同目錄下的 config.json。

1. 瀏覽與新增排程 (Browse & Add)：

混合搜尋：可以直接輸入 ID (如 272) 直達，或是輸入 關鍵字 (如 vmware) 進行搜尋。

直接瀏覽：不輸入任何字直接按 Enter，可列出所有規則集。

選擇層級：選定規則集後，可決定要控制「整個規則集」或是進入挑選「單條規則」。

設定模式：

Schedule: 週期性 (如每天上班時間開啟)。

Expiration: 設定過期時間 (如 2025-12-31 之後自動關閉並移除)。

2. 列表 (Grouped View)：

以樹狀結構顯示目前的排程。

狀態燈號：✔ ON (生效中) / ✖ OFF (已關閉)。

排程指標：★ 代表母集有排程，● 代表子集有排程。

3. 刪除排程：

輸入 ID 移除排程控管。程式會自動將 PCE 上 Description 欄位的排程註記清除。

4. 立即檢查 (Dry Run)：

手動觸發一次邏輯檢查，用於測試設定是否正確。

⚙️ 背景服務設定 (Systemd)
為了讓排程自動運作（即使登出或重開機），請設定 Systemd 服務。

1. 建立 Service 檔案
建立檔案 /etc/systemd/system/illumio-scheduler.service：

Ini, TOML
[Unit]
Description=Illumio Rule Auto-Scheduler Service
After=network.target

[Service]
Type=simple
User=root
# 設定工作目錄 (非常重要，確保能讀取到 config.json)
WorkingDirectory=/opt/illumio_scheduler
# 指向 venv 中的 python，並加上 --monitor 參數
ExecStart=/opt/illumio_scheduler/venv/bin/python3 illumio_scheduler.py --monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
2. 啟動服務
Bash
# 重新讀取設定
sudo systemctl daemon-reload

# 啟動服務並設定開機自啟
sudo systemctl enable --now illumio-scheduler

# 檢查狀態
sudo systemctl status illumio-scheduler
3. 查看運作日誌
若要查看背景執行的紀錄（例如是否有觸發切換）：

Bash
sudo journalctl -u illumio-scheduler -f
⚠️ 重要注意事項
時間同步 (NTP)：

請確保執行腳本的 Linux 主機時間是準確的。

使用 timedatectl 檢查時區。腳本使用 datetime.now()，即依據伺服器的本地時間進行判斷。

API 權限：

使用的 API Key 必須具備 Global Admin 或該規則集的 Ruleset Provisioner 權限，否則無法寫入 Description 或執行發布。

發布機制 (Provisioning)：

本工具在變更狀態後會自動觸發 Provision。

注意：Provision 是以 RuleSet 為單位。如果該 RuleSet 中有其他「人為修改但尚未發布」的草稿 (Draft)，也會被此工具一併發布出去。建議保持 Draft 乾淨。

檔案保存：

config.json: 存放 API 金鑰，請妥善保護。

rule_schedules.json: 存放排程資料庫，請勿隨意手動修改。
