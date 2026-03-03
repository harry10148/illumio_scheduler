# API Cookbook — Illumio REST API with Python

🌐 [English](API_Cookbook_en.md) | [繁體中文](API_Cookbook_zh.md)

---

## Overview

This cookbook teaches you how to call the **Illumio PCE REST API** directly using Python.
No external libraries required — all examples use Python's built-in `urllib` and `json`.

Perfect for **SIEM/SOAR engineers** who want to automate Illumio policy management.

---

## Table of Contents

1. [Authentication Setup](#1-authentication-setup)
2. [Making API Calls](#2-making-api-calls)
3. [Common Operations](#3-common-operations)
   - [List All RuleSets](#31-list-all-rulesets)
   - [Get Rules in a RuleSet](#32-get-rules-in-a-ruleset)
   - [Enable/Disable a Rule](#33-enabledisable-a-rule)
   - [Update a Rule Description](#34-update-a-rule-description)
   - [Provision Changes](#35-provision-changes)
   - [List All Labels](#36-list-all-labels)
4. [Draft vs. Active Explained](#4-draft-vs-active-explained)
5. [Error Handling](#5-error-handling)
6. [Rate Limits](#6-rate-limits)
7. [Complete End-to-End Script](#7-complete-end-to-end-script)

---

## 1. Authentication Setup

Illumio uses **HTTP Basic Authentication** with an API Key and Secret.

```python
import urllib.request
import ssl
import base64
import json

# --- Configuration ---
PCE_URL    = "https://your-pce.example.com:8443"
ORG_ID     = "1"
API_KEY    = "api_xxxxxxxxxxxxxxxx"
API_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# --- Build auth header ---
credentials = f"{API_KEY}:{API_SECRET}"
auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

# --- SSL context (set verify=False for self-signed certs) ---
ssl_ctx = ssl.create_default_context()
# ssl_ctx.check_hostname = False      # Uncomment for self-signed
# ssl_ctx.verify_mode = ssl.CERT_NONE # Uncomment for self-signed
```

> **Note**: The API Key needs **Ruleset Provisioner** or **Global Organization Owner** permissions for write operations.

---

## 2. Making API Calls

Here's a reusable helper function:

```python
def api_request(method, endpoint, payload=None):
    """
    Make an HTTP request to the Illumio PCE API.
    
    Args:
        method: 'GET', 'PUT', 'POST', or 'DELETE'
        endpoint: API path (e.g., '/orgs/1/labels')
        payload: dict to send as JSON body (for PUT/POST)
    
    Returns:
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

## 3. Common Operations

### 3.1 List All RuleSets

```python
status, rulesets = api_request('GET', f'/orgs/{ORG_ID}/sec_policy/draft/rule_sets?max_results=10000')

if status == 200:
    print(f"Found {len(rulesets)} rulesets:")
    for rs in rulesets:
        state = "Enabled" if rs.get('enabled') else "Disabled"
        print(f"  [{state}] {rs['name']} (href: {rs['href']})")
```

> **Important**: The PCE default limit is **500 items** per GET collection. Always use `max_results` to get more.

### 3.2 Get Rules in a RuleSet

```python
# Get a specific ruleset by its ID
rs_id = "3"
status, ruleset = api_request('GET', f'/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}')

if status == 200:
    print(f"RuleSet: {ruleset['name']}")
    for rule in ruleset.get('rules', []):
        state = "ON" if rule.get('enabled') else "OFF"
        desc = rule.get('description', '(no description)')
        print(f"  [{state}] {rule['href']} — {desc}")
```

### 3.3 Enable/Disable a Rule

```python
def toggle_rule(rule_href, enabled):
    """Toggle a rule's enabled state."""
    # PUT must target the DRAFT version
    draft_href = rule_href.replace('/active/', '/draft/')
    
    status, _ = api_request('PUT', draft_href, {'enabled': enabled})
    
    if status == 204:
        action = "Enabled" if enabled else "Disabled"
        print(f"✅ {action} rule: {rule_href}")
        return True
    else:
        print(f"❌ Failed to toggle rule (HTTP {status})")
        return False

# Example: disable a rule
toggle_rule('/orgs/1/sec_policy/draft/rule_sets/3/sec_rules/9', False)
```

> **Key Point**: PUT operations return **204 No Content** on success (no response body).

### 3.4 Update a Rule Description

```python
def update_description(rule_href, new_description):
    """Update the description field of a rule."""
    draft_href = rule_href.replace('/active/', '/draft/')
    
    status, _ = api_request('PUT', draft_href, {'description': new_description})
    
    if status == 204:
        print(f"✅ Updated description: {new_description}")
    else:
        print(f"❌ Failed to update description (HTTP {status})")

# Example
update_description(
    '/orgs/1/sec_policy/draft/rule_sets/3/sec_rules/9',
    'Temporary access — expires 2025-12-31'
)
```

> **Note**: The `description` field has **no character limit** according to the API documentation.

### 3.5 Provision Changes

After modifying draft objects, you must **provision** them to make them active:

```python
def provision(ruleset_href, description="API provisioned change"):
    """Provision a ruleset and its rules."""
    payload = {
        "update_description": description,
        "change_subset": {
            "rule_sets": [{"href": ruleset_href}]
        }
    }
    
    status, resp = api_request('POST', f'/orgs/{ORG_ID}/sec_policy', payload)
    
    if status in (200, 201):
        print(f"✅ Provisioned: {ruleset_href}")
        return True
    else:
        print(f"❌ Provisioning failed (HTTP {status})")
        return False

# Example
provision('/orgs/1/sec_policy/draft/rule_sets/3')
```

### 3.6 List All Labels

```python
status, labels = api_request('GET', f'/orgs/{ORG_ID}/labels?max_results=10000')

if status == 200:
    for label in labels:
        print(f"  {label.get('key')}:{label.get('value')} → {label['href']}")
```

---

## 4. Draft vs. Active Explained

Illumio uses a **two-phase commit model** for security policy objects:

| Concept | Description |
|---------|-------------|
| **Draft** | Unpublished changes. All write operations (PUT, POST, DELETE) work on draft. |
| **Active** | Published (provisioned) policy. Read-only for GET operations. |
| **Provision** | The act of publishing draft changes to active. Done via `POST /sec_policy`. |

### URL Patterns

```
GET  /sec_policy/draft/rule_sets     → Get draft (current working copy)
GET  /sec_policy/active/rule_sets    → Get active (provisioned copy)
PUT  /sec_policy/draft/rule_sets/3   → Modify draft (ONLY draft allowed)
POST /sec_policy                     → Provision draft → active
```

### update_type Field

When reading objects, the `update_type` field tells you the draft status:

| Value | Meaning |
|-------|---------|
| `null` | No pending changes (draft = active) |
| `"create"` | Newly created, not yet provisioned |
| `"update"` | Modified since last provision |
| `"delete"` | Marked for deletion, not yet provisioned |

---

## 5. Error Handling

Common HTTP status codes:

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 200 | OK | Successful GET |
| 201 | Created | Successful POST (new object) |
| 204 | No Content | Successful PUT/DELETE |
| 400 | Bad Request | Malformed JSON or invalid parameters |
| 401 | Unauthorized | Invalid API Key/Secret |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invalid endpoint or object doesn't exist |
| 406 | Invalid Payload | Wrong Content-Type or schema validation failed |
| 429 | Too Many Requests | Rate limit exceeded (see below) |

---

## 6. Rate Limits

| Limit | Value |
|-------|-------|
| Requests per minute per API Key | **500** |
| GET collection default max results | **500** (use `max_results` to override, max 10000) |
| Bulk operations | **1,000 items** per request |
| Resource name length | **255 characters** |
| Description length | **No limit** |

---

## 7. Complete End-to-End Script

Here's a full working script that disables a rule and provisions the change:

```python
#!/usr/bin/env python3
"""
Illumio API Example: Disable a rule and provision the change.
Usage: python disable_rule.py <ruleset_id> <rule_id>
"""
import urllib.request
import ssl
import base64
import json
import sys

# ── Configuration ──
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
        print("Usage: python disable_rule.py <ruleset_id> <rule_id>")
        sys.exit(1)
    
    rs_id = sys.argv[1]
    rule_id = sys.argv[2]
    
    rule_href = f"/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}/sec_rules/{rule_id}"
    rs_href = f"/orgs/{ORG_ID}/sec_policy/draft/rule_sets/{rs_id}"
    
    # Step 1: Disable the rule
    print(f"Disabling rule: {rule_href}")
    status, _ = api_request('PUT', rule_href, {'enabled': False})
    if status != 204:
        print(f"Failed! HTTP {status}")
        sys.exit(1)
    print("✅ Rule disabled (draft)")
    
    # Step 2: Provision the change
    print(f"Provisioning ruleset: {rs_href}")
    payload = {
        "update_description": "Disabled rule via API script",
        "change_subset": {
            "rule_sets": [{"href": rs_href}]
        }
    }
    status, _ = api_request('POST', f'/orgs/{ORG_ID}/sec_policy', payload)
    if status not in (200, 201):
        print(f"Provision failed! HTTP {status}")
        sys.exit(1)
    print("✅ Provisioned successfully!")


if __name__ == '__main__':
    main()
```

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Overview](README_en.md) | Program introduction and features |
| [User Manual](User_Manual_en.md) | Step-by-step operating instructions |
| [Architecture](Architecture_en.md) | Code structure and extension guide |
