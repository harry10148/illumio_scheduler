# Illumio Rule Scheduler

![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-gold?logo=python&logoColor=white)

An automated rule scheduling tool for **Illumio Core (PCE)**. Supports **Web GUI**, **CLI**, and **Daemon** modes. Core engine uses only Python standard library — Flask is the only optional dependency (for Web GUI only).

---

## 📖 Complete Documentation & Manuals

For comprehensive guides on how to install, configure, deploy, and operate the Illumio Rule Scheduler (including detailed explanations of the Web GUI layout, language translations, themes, and CLI modes), please refer to our official User Manuals located in the `docs` folder:

- 🇺🇸 **English**: [docs/User_Manual_en.md](docs/User_Manual_en.md)
- 🇹🇼 **繁體中文**: [docs/User_Manual_zh.md](docs/User_Manual_zh.md)

---

## ⚡ Quick Start / Installation

**Requirement**: Python 3.8+
**Web GUI (Optional)**: `pip install flask`

**Linux / macOS**:
```bash
sudo mkdir -p /opt/illumio_scheduler
cd /opt/illumio_scheduler
chmod +x illumio_scheduler.py
```

**Windows**:
1. Install [Python 3](https://www.python.org/downloads/) (check "Add to PATH")
2. Place the project directory anywhere (e.g. `C:\illumio_scheduler`)

### Run the App
Launch the Flask-powered Web GUI for a complete visual experience:
```bash
python illumio_scheduler.py --gui --port 5000
```
*(The native Web GUI seamlessly supports full ultra-wide responsiveness and Light/Dark themes derived directly from Illumio brand guidelines).*

If running in a pure terminal environment via SSH:
```bash
python illumio_scheduler.py
```

### Run as a Background Daemon
To deploy permanently as a service monitor (so schedules apply continuously):
```bash
python illumio_scheduler.py --monitor
```
*(See the [User Manual](docs/User_Manual_en.md) for Windows NSSM and Linux Systemd daemon scripts).*

---

## 📁 Project Structure

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py          # Entry point (CLI / GUI / Daemon)
├── src/
│   ├── core.py                   # Core engine (API, DB, scheduling logic)
│   ├── cli_ui.py                 # CLI interactive interface
│   ├── gui_ui.py                 # Flask Web GUI (dark/light theme SPA)
│   └── i18n.py                   # Internationalisation (EN/ZH string tables)
├── deploy/                       # Systemd & NSSM Deployment scripts
├── docs/                         
│   ├── User_Manual_en.md         # English User Manual
│   └── User_Manual_zh.md         # Traditional Chinese User Manual
└── README.md
```

---

## 📄 License

This project is provided as-is for internal use.
