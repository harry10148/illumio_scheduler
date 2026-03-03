# User Manual — Illumio Rule Scheduler

🌐 [English](User_Manual_en.md) | [繁體中文](User_Manual_zh.md)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Configuration](#2-configuration)
3. [Running the Application](#3-running-the-application)
4. [Web GUI Walkthrough](#4-web-gui-walkthrough)
5. [CLI Walkthrough](#5-cli-walkthrough)
6. [Deploying as a System Service](#6-deploying-as-a-system-service)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.7 or higher |
| Flask | Optional — only for Web GUI mode (`pip install flask`) |
| PCE API Key | Must have **Ruleset Provisioner** or **Global Organization Owner** role |
| Network | HTTPS access to the PCE (default port 8443) |

### Creating an API Key

1. Log in to the Illumio PCE web console.
2. Navigate to **Settings → API Keys → Add**.
3. Note down the **API Key ID** and **API Secret** (the secret is shown only once).
4. Ensure the key has at minimum **Ruleset Provisioner** permissions.

---

## 2. Configuration

### Quick Setup

```bash
cp config.json.example config.json
```

Edit `config.json` with your PCE credentials:

```json
{
    "pce_url": "https://your-pce.example.com:8443",
    "org_id": "1",
    "api_key": "api_xxxxxxxxxxxxxxxx",
    "api_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "ssl_verify": true,
    "lang": "en"
}
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `pce_url` | ✅ | Full PCE URL with port (e.g., `https://pce.company.com:8443`) |
| `org_id` | ✅ | Organization ID (usually `1`) |
| `api_key` | ✅ | API Key ID from the PCE |
| `api_secret` | ✅ | API Secret (stored in plaintext — secure file permissions) |
| `ssl_verify` | ❌ | Set to `false` for self-signed certificates (default: `true`) |
| `check_interval_seconds` | ❌ | Schedule engine check interval in seconds (default: `300` = 5 min) |
| `lang` | ❌ | UI language: `"en"` (English) or `"zh"` (繁體中文) |
| `alert_email` | ❌ | Email address for schedule trigger notifications |
| `smtp_host` | ❌ | SMTP server hostname |
| `smtp_port` | ❌ | SMTP server port (default: `587`) |
| `smtp_auth` | ❌ | Enable SMTP authentication (`true`/`false`) |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ILLUMIO_PORT` | Override default Web GUI port (default: `5002`) |
| `ILLUMIO_CHECK_INTERVAL` | Override schedule check interval in seconds (fallback if `check_interval_seconds` not set in config.json) |

---

## 3. Running the Application

### Web GUI Mode

```bash
python illumio_scheduler.py --gui
python illumio_scheduler.py --gui --port 8080   # custom port
```

Opens a browser automatically at `http://localhost:5002`.

### CLI Mode

```bash
python illumio_scheduler.py
```

Launches an interactive terminal menu.

### Daemon Mode

```bash
python illumio_scheduler.py --monitor
```

Runs the schedule engine continuously, checking every 300 seconds (5 min) by default. You can adjust this via `check_interval_seconds` in `config.json`.

---

## 4. Web GUI Walkthrough

### Tab 1: Browse & Add Schedules

1. **Browse RuleSets** — The left pane lists all rulesets from the PCE. Use the search bar to filter by name.
2. **View Rules** — Click a ruleset to expand its rules in the right pane.
3. **Add Schedule** — Click a rule or ruleset row, then click **"+ Add Schedule"** to open the scheduling modal.

#### Creating a Recurring Schedule

1. Select **Schedule Type: Recurring**.
2. Choose **Action**:
   - *Enable in Window* — Rule is ON during the time window, OFF outside.
   - *Disable in Window* — Rule is OFF during the time window, ON outside.
3. Enter **Days** (comma-separated): `Monday,Tuesday,Wednesday,Thursday,Friday`
4. Enter **Start Time** and **End Time**: e.g., `08:00` and `18:00`
5. Click **Save**.

#### Creating a One-Time Expiration

1. Select **Schedule Type: One-Time Expiration**.
2. Enter **Expiration Date/Time**: e.g., `2025-12-31 23:59`
3. Click **Save**.

### Tab 2: Scheduled Tasks

View all configured schedules. You can:
- See current enabled/disabled status
- Delete schedules (select rows → click **Delete Selected**)

### Tab 3: Run Engine

Click **"Run Check Now"** to manually trigger the schedule engine. The log panel shows what actions were executed.

### Tab 4: Settings

Update PCE connection settings and language preference without editing `config.json` manually.

---

## 5. CLI Walkthrough

The CLI presents a numbered menu:

```
========== Illumio Rule Scheduler ==========
1. Browse & Manage RuleSets
2. View Scheduled Tasks
3. Run Schedule Check Now
4. Settings
5. Exit
=============================================
```

### Browse & Manage

1. Select option `1` to list all rulesets.
2. Enter the ID of a ruleset to view its rules.
3. Select a rule and choose an action:
   - Add Recurring Schedule
   - Add One-Time Expiration
   - Remove Schedule

### Run Check

Select option `3` to immediately run the schedule engine and see results.

---

## 6. Deploying as a System Service

### Windows (NSSM)

Use the provided PowerShell script:

```powershell
.\deploy\deploy_windows.ps1
```

This installs the scheduler as a Windows service using [NSSM](https://nssm.cc/).

### Linux (systemd)

1. Copy the service file:
   ```bash
   sudo cp deploy/illumio-scheduler.service /etc/systemd/system/
   ```
2. Edit the service file to set correct paths.
3. Enable and start:
   ```bash
   sudo systemctl enable illumio-scheduler
   sudo systemctl start illumio-scheduler
   ```

---

## 7. Troubleshooting

### Cannot connect to PCE

- Verify `pce_url` includes the port (e.g., `:8443`).
- If using self-signed certificates, set `"ssl_verify": false`.
- Ensure the API Key has not expired.

### Rules not being toggled

- Check that the API Key has **Ruleset Provisioner** or higher permissions.
- Verify the schedule is correctly configured (check the **Scheduled Tasks** tab).
- Run the engine manually to see detailed logs.

### GET returns fewer rulesets than expected

- The tool uses `max_results=10000` to overcome the PCE's 500-item default limit.
- If you have more than 10,000 rulesets, contact your PCE administrator.

### Web GUI won't start

- Ensure Flask is installed: `pip install flask`
- Check if the port is already in use: try `--port 8080`

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Overview](README_en.md) | Program introduction and features |
| [Architecture](Architecture_en.md) | Code structure and extension guide |
| [API Cookbook](API_Cookbook_en.md) | Python examples for Illumio API automation |
