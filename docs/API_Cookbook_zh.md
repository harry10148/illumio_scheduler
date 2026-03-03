# API 教學手冊 — 用 Python 呼叫 Illumio REST API

🌐 [English](API_Cookbook_en.md) | [繁體中文](API_Cookbook_zh.md)

---

## 總覽

本手冊教你如何直接用 Python 呼叫 **Illumio PCE REST API**。
不需要外部套件 — 所有範例僅使用 Python 內建的 `urllib` 和 `json`。

適合 **SIEM/SOAR 工程師**想要自動化 Illumio 策略管理的場景。

---

## 目錄

1. [認證設定](#1-認證設定)
2. [發送 API 請求](#2-發送-api-請求)
3. [常用操作](#3-常用操作)
   - [列出所有 RuleSet](#31-列出所有-ruleset)
   - [取得 RuleSet 內的 Rules](#32-取得-ruleset-內的-rules)
   - [啟用/停用 Rule](#33-啟用停用-rule)
   - [更新 Rule 描述](#34-更新-rule-描述)
   - [發布變更](#35-發布變更)
   - [列出所有 Labels](#36-列出所有-labels)
4. [Draft vs. Active 觀念](#4-draft-vs-active-觀念)
5. [錯誤處理](#5-錯誤處理)
6. [速率限制](#6-速率限制)
7. [完整端對端腳本](#7-完整端對端腳本)

---

## 1. 認證設定

Illumio 使用 **HTTP Basic Authentication**，搭配 API Key 和 Secret。

```python
import urllib.request
import ssl
import base64
import json

# --- 設定 ---
PCE_URL    = "https://your-pce.example.com:8443"
ORG_ID     = "1"
API_KEY    = "api_xxxxxxxxxxxxxxxx"
API_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# --- 建立 Auth Header ---
credentials = f"{API_KEY}:{API_SECRET}"
auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

# --- SSL 設定（自簽憑證需取消註解） ---
ssl_ctx = ssl.create_default_context()
# ssl_ctx.check_hostname = False      # 自簽憑證取消此行註解
# ssl_ctx.verify_mode = ssl.CERT_NONE # 自簽憑證取消此行註解
```

> **注意**：API Key 需要 **Ruleset Provisioner** 或 **Global Organization Owner** 權限才能執行寫入操作。

---

## 2. 發送 API 請求

可重用的輔助函式：

```python
def api_request(method, endpoint, payload=None):
    """
    對 Illumio PCE API 發送 HTTP 請求。
    
    參數:
        method: 'GET', 'PUT', 'POST', 或 'DELETE'
        endpoint: API 路徑 (例如 '/orgs/1/labels')
        payload: 字典作為 JSON body (用於 PUT/POST)
    
    回傳:
        (status_code, response_data)
    """
    url = f"{PCE_URL}/api/v2{endpoint}"
    
    data = None
    if payload:
        data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', auth_header)
    
    if method in ('PUT', 'POST'):
        req.add_header('Content-Type', 'application/json')
    else:
        req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, context=ssl_ctx) as resp:
            body = resp.read()
            status = resp.status
            if body:
                return status, json.loads(body.decode('utf-8'))
            return status, {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        print(f"HTTP {e.code}: {body}")
        return e.code, {}
```

---

## 3. 常用操作

### 3.1 列出所有 RuleSet

```python
status, rulesets = api_request('GET', f'/orgs/{ORG_ID}/sec_policy/draft/rule_sets?max_results=10000')

if status == 200:
    print(f"找到 {len(rulesets)} 個規則集：")
    for rs in rulesets:
        state = "啟用" if rs.get('enabled') else "停用"
        print(f"  [{state}] {rs['name']} (href: {rs['href']})")
```

> **重要**：PCE 預設限制每次 GET 最多回傳 **500 筆**。務必使用 `max_results` 取得更多。

### 3.2 取得 RuleSet 內的 Rules

```python
# 透過 ID 取得特定規則集
rs_id = "3"
status, ruleset = api_request('GET', f'/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}')

if status == 200:
    print(f"規則集: {ruleset['name']}")
    for rule in ruleset.get('rules', []):
        state = "開" if rule.get('enabled') else "關"
        desc = rule.get('description', '(無描述)')
        print(f"  [{state}] {rule['href']} — {desc}")
```

### 3.3 啟用/停用 Rule

```python
def toggle_rule(rule_href, enabled):
    """切換規則的啟用狀態。"""
    # PUT 必須指向 DRAFT 版本
    draft_href = rule_href.replace('/active/', '/draft/')
    
    status, _ = api_request('PUT', draft_href, {'enabled': enabled})
    
    if status == 204:
        action = "啟用" if enabled else "停用"
        print(f"✅ 已{action}規則: {rule_href}")
        return True
    else:
        print(f"❌ 切換規則失敗 (HTTP {status})")
        return False

# 範例：停用一條規則
toggle_rule('/orgs/1/sec_policy/draft/rule_sets/3/sec_rules/9', False)
```

> **重點**：PUT 成功回傳 **204 No Content**（沒有回應 body）。

### 3.4 更新 Rule 描述

```python
def update_description(rule_href, new_description):
    """更新規則的描述欄位。"""
    draft_href = rule_href.replace('/active/', '/draft/')
    
    status, _ = api_request('PUT', draft_href, {'description': new_description})
    
    if status == 204:
        print(f"✅ 已更新描述: {new_description}")
    else:
        print(f"❌ 更新描述失敗 (HTTP {status})")

# 範例
update_description(
    '/orgs/1/sec_policy/draft/rule_sets/3/sec_rules/9',
    '臨時存取 — 到期日 2025-12-31'
)
```

> **備注**：API 文件確認 `description` 欄位**沒有字元長度限制**。

### 3.5 發布變更

修改草稿物件後，需要**發布 (Provision)** 才能生效：

```python
def provision(ruleset_href, description="API 自動發布"):
    """發布規則集及其規則。"""
    payload = {
        "update_description": description,
        "change_subset": {
            "rule_sets": [{"href": ruleset_href}]
        }
    }
    
    status, resp = api_request('POST', f'/orgs/{ORG_ID}/sec_policy', payload)
    
    if status in (200, 201):
        print(f"✅ 已發布: {ruleset_href}")
        return True
    else:
        print(f"❌ 發布失敗 (HTTP {status})")
        return False

# 範例
provision('/orgs/1/sec_policy/draft/rule_sets/3')
```

### 3.6 列出所有 Labels

```python
status, labels = api_request('GET', f'/orgs/{ORG_ID}/labels?max_results=10000')

if status == 200:
    for label in labels:
        print(f"  {label.get('key')}:{label.get('value')} → {label['href']}")
```

---

## 4. Draft vs. Active 觀念

Illumio 使用**兩階段提交模型**管理安全策略物件：

| 概念 | 說明 |
|------|------|
| **Draft（草稿）** | 未發布的變更。所有寫入操作（PUT/POST/DELETE）都在草稿上執行。 |
| **Active（已發布）** | 已發布的策略。GET 時可讀取。 |
| **Provision（發布）** | 將草稿變更推送到已發布狀態。透過 `POST /sec_policy` 執行。 |

### URL 模式

```
GET  /sec_policy/draft/rule_sets     → 取得草稿（目前工作副本）
GET  /sec_policy/active/rule_sets    → 取得已發布（唯讀）
PUT  /sec_policy/draft/rule_sets/3   → 修改草稿（只能對草稿操作）
POST /sec_policy                     → 發布 draft → active
```

### update_type 欄位

讀取物件時，`update_type` 欄位告訴你草稿狀態：

| 值 | 意義 |
|----|------|
| `null` | 無待處理變更（草稿 = 已發布） |
| `"create"` | 新建立，尚未發布 |
| `"update"` | 上次發布後有修改 |
| `"delete"` | 標記刪除，尚未發布 |

---

## 5. 錯誤處理

常見 HTTP 狀態碼：

| 代碼 | 意義 | 常見原因 |
|------|------|----------|
| 200 | OK | GET 成功 |
| 201 | Created | POST 成功（建立新物件） |
| 204 | No Content | PUT/DELETE 成功 |
| 400 | Bad Request | JSON 格式錯誤或參數無效 |
| 401 | Unauthorized | API Key/Secret 無效 |
| 403 | Forbidden | 權限不足 |
| 404 | Not Found | 端點無效或物件不存在 |
| 406 | Invalid Payload | Content-Type 錯誤或 Schema 驗證失敗 |
| 429 | Too Many Requests | 超過速率限制（見下方） |

---

## 6. 速率限制

| 限制 | 數值 |
|------|------|
| 每分鐘每 API Key 請求數 | **500** |
| GET collection 預設最大結果數 | **500**（用 `max_results` 覆蓋，最大 10000） |
| 批量操作 | 每次 **1,000 筆** |
| 資源名稱長度 | **255 字元** |
| 描述 (description) 長度 | **無限制** |

---

## 7. 完整端對端腳本

以下是一個完整的工作腳本，停用規則並發布變更：

```python
#!/usr/bin/env python3
"""
Illumio API 範例：停用一條規則並發布變更。
用法: python disable_rule.py <ruleset_id> <rule_id>
"""
import urllib.request
import ssl
import base64
import json
import sys

# ── 設定 ──
PCE_URL    = "https://your-pce.example.com:8443"
ORG_ID     = "1"
API_KEY    = "api_xxxxxxxxxxxxxxxx"
API_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

credentials = f"{API_KEY}:{API_SECRET}"
auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()
ssl_ctx = ssl.create_default_context()


def api_request(method, endpoint, payload=None):
    url = f"{PCE_URL}/api/v2{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', auth_header)
    if method in ('PUT', 'POST'):
        req.add_header('Content-Type', 'application/json')
    else:
        req.add_header('Accept', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ssl_ctx) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        return e.code, {}


def main():
    if len(sys.argv) != 3:
        print("用法: python disable_rule.py <ruleset_id> <rule_id>")
        sys.exit(1)
    
    rs_id = sys.argv[1]
    rule_id = sys.argv[2]
    
    rule_href = f"/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}/sec_rules/{rule_id}"
    rs_href = f"/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}"
    
    # 步驟 1：停用規則
    print(f"正在停用規則: {rule_href}")
    status, _ = api_request('PUT', rule_href, {'enabled': False})
    if status != 204:
        print(f"失敗！HTTP {status}")
        sys.exit(1)
    print("✅ 規則已停用（草稿）")
    
    # 步驟 2：發布變更
    print(f"正在發布規則集: {rs_href}")
    payload = {
        "update_description": "透過 API 腳本停用規則",
        "change_subset": {
            "rule_sets": [{"href": rs_href}]
        }
    }
    status, _ = api_request('POST', f'/orgs/{ORG_ID}/sec_policy', payload)
    if status not in (200, 201):
        print(f"發布失敗！HTTP {status}")
        sys.exit(1)
    print("✅ 發布成功！")


if __name__ == '__main__':
    main()
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [功能總覽](README_zh.md) | 程式介紹與功能 |
| [操作手冊](User_Manual_zh.md) | 逐步操作指南 |
| [程式架構](Architecture_zh.md) | 程式碼結構與擴展指南 |
