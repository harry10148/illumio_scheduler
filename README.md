# Illumio Rule Scheduler (v4.2.0)

![Version](https://img.shields.io/badge/Version-v4.2.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-gold?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)

> [English](README.md) | [繁體中文](README.zh-TW.md)

---

An automated rule scheduling tool for **Illumio Core (PCE)**. Supports both **GUI** and **CLI** modes with **zero external dependencies** — runs on any system with Python 3.8+ out of the box.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📅 **Recurring Schedule** | Enable/disable rules on a weekly schedule (supports cross-midnight, e.g. 22:00–06:00) |
| ⏳ **Auto-Expiration** | One-time rules that auto-disable and self-delete after a set time |
| 🖥️ **Web GUI + CLI** | Flask-powered Web GUI (auto-opens browser); ANSI CLI for SSH/terminal |
| 👁️ **Dual Indicators** | ★ = RuleSet scheduled, ● = child rule scheduled |
| 📝 **Note Integration** | Automatically writes schedule info into the Illumio rule Description field |
| 🔄 **Live Sync** | Real-time PCE state verification during listing |
| 🛡️ **Zero Dependencies** | No `pip install` needed — uses only Python standard library |

---

## 📁 Project Structure

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py          # Entry point (CLI / GUI / Daemon)
├── src/
│   ├── __init__.py
│   ├── core.py                   # Core engine (API, DB, scheduling logic)
│   ├── cli_ui.py                 # CLI interactive interface
│   └── gui_ui.py                 # Flask Web GUI (dark theme SPA)
├── deploy/
│   ├── deploy_windows.ps1        # Windows NSSM service deployment
│   └── illumio-scheduler.service # Linux systemd unit file
├── config.json                   # API settings (generated at runtime)
├── rule_schedules.json           # Schedule database (generated at runtime)
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

---

## 🚀 Usage

### GUI Mode (recommended for desktop)
```bash
python illumio_scheduler.py --gui
```

### CLI Mode (recommended for SSH / terminal)
```bash
python illumio_scheduler.py
```
> You can also press `5` in the CLI menu to launch the GUI directly.

### Daemon Mode (background monitoring)
```bash
python illumio_scheduler.py --monitor
```

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

## ⚠️ Notes & Troubleshooting

1. **Clock accuracy** — Ensure the host timezone is correct (`timedatectl` / Windows time settings)
2. **API permissions** — The API Key must have **Global Admin** or **Ruleset Provisioner** privileges
3. **Provisioning scope** — Provisioning is per-RuleSet; unpublished drafts within the same RuleSet will also be published
4. **Check interval** — Default is 300 seconds; adjust with env var `ILLUMIO_CHECK_INTERVAL=<seconds>`
5. **Security** — API credentials are stored in plaintext in `config.json`; set appropriate directory permissions
