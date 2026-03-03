# 🕒 Illumio Rule Scheduler

**Automate the enable/disable of Illumio PCE security policy rules and rulesets on a schedule.**

自動化啟用／停用 Illumio PCE 安全策略規則和規則集的排程工具。

---

## 📖 Documentation / 文件

| Document | English | 繁體中文 |
|----------|---------|----------|
| **Overview & Introduction** | [README_en.md](docs/README_en.md) | [README_zh.md](docs/README_zh.md) |
| **User Manual** | [User_Manual_en.md](docs/User_Manual_en.md) | [User_Manual_zh.md](docs/User_Manual_zh.md) |
| **Architecture & Specs** | [Architecture_en.md](docs/Architecture_en.md) | [Architecture_zh.md](docs/Architecture_zh.md) |
| **API Cookbook** | [API_Cookbook_en.md](docs/API_Cookbook_en.md) | [API_Cookbook_zh.md](docs/API_Cookbook_zh.md) |

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd illumio_Rule-Scheduler

# 2. Configure
cp config.json.example config.json
# Edit config.json with your PCE URL, Org ID, API Key, and API Secret

# 3. Run (choose one)
python illumio_scheduler.py              # CLI interactive mode
python illumio_scheduler.py --gui        # Web GUI (requires: pip install flask)
python illumio_scheduler.py --monitor    # Daemon mode (background monitoring)
```

---

## 📁 Project Structure

```
illumio_Rule-Scheduler/
├── illumio_scheduler.py      # Entry point
├── config.json               # PCE connection settings (user-created)
├── config.json.example       # Example configuration
├── rule_schedules.json       # Local schedule database (auto-generated)
├── src/
│   ├── core.py               # Core engine: API client, scheduler, config
│   ├── cli_ui.py             # CLI interactive interface
│   ├── gui_ui.py             # Flask Web GUI (SPA)
│   └── i18n.py               # Internationalization strings (EN/ZH)
├── docs/                     # Documentation (EN + ZH)
└── deploy/                   # Service deployment scripts (Windows/Linux)
```

---

## 📜 License

MIT License
