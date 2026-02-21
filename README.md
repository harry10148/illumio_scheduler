# Illumio Rule Scheduler (v4.2.0)

![Version](https://img.shields.io/badge/Version-v4.2.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-gold?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)

> [English](README.md) | [繁體中文](README.zh-TW.md)

---

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

## 🚀 Usage

### Web GUI Mode (recommended for desktop)
```bash
python illumio_scheduler.py --gui
```
- Starts Flask server on `http://localhost:5000`
- Auto-opens browser
- Dark-themed single-page application

### CLI Mode (recommended for SSH / terminal)
```bash
python illumio_scheduler.py
```
**Main Menu:**
```
=== Illumio Scheduler v4.2 (Hybrid UI) ===
0. Configure API
1. Schedule Management (Browse/List/Edit/Delete)
2. Run Check Now
3. Open Web GUI
4. Language [EN]
q. Quit
```

### Daemon Mode (background monitoring)
```bash
python illumio_scheduler.py --monitor
```
> Runs the schedule engine in a loop (default: every 300 seconds)

---

## ⚙️ Background Service Deployment

### Windows (NSSM recommended)

1. Download [NSSM](http://nssm.cc/download)
2. Run as **Administrator**:
   ```powershell
   .\deploy\deploy_windows.ps1 -NssmPath "C:\path\to\nssm.exe"
   ```
3. The service installs and starts automatically (name: `IllumioScheduler`)

**Alternative: Task Scheduler**
- Create Task → Trigger: At system startup → Action: `python illumio_scheduler.py --monitor`

### Linux (Systemd)

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
