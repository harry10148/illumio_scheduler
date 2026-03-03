# Illumio Rule Scheduler — Overview & Introduction

🌐 [English](README_en.md) | [繁體中文](README_zh.md)

---

## What is Illumio Rule Scheduler?

Illumio Rule Scheduler is a Python-based automation tool that schedules the enabling and disabling of **security policy rules** and **rulesets** in the [Illumio Policy Compute Engine (PCE)](https://www.illumio.com/).

### Why?

The Illumio PCE does not natively support time-based rule scheduling. This tool fills that gap by:

- **Recurring Schedules** — Automatically enable rules during business hours (e.g., Mon–Fri 08:00–18:00) and disable them outside that window.
- **One-Time Expiration** — Set a rule to automatically disable after a specific date/time (e.g., a temporary firewall exception).

### How It Works

1. You configure schedules via the **Web GUI**, **CLI**, or directly in the JSON database.
2. The tool appends a schedule tag to the rule's `description` field in the PCE (e.g., `[📅 Recurring: Mon-Fri 08:00-18:00 ENABLE in window]`).
3. A background monitor periodically checks the current time against all configured schedules.
4. When a schedule triggers, the tool calls the Illumio REST API to toggle the rule's `enabled` state and provisions the change.

### Key Features

| Feature | Description |
|---------|-------------|
| **Three Operating Modes** | Web GUI (Flask), CLI (interactive terminal), Daemon (background service) |
| **Recurring Schedules** | Configure day-of-week and time windows for automatic enable/disable |
| **One-Time Expiration** | Set rules to expire at a specific date/time |
| **Dependency-Aware Provisioning** | Automatically discovers and provisions dependent objects |
| **Bilingual UI** | English and Traditional Chinese (繁體中文) |
| **Light/Dark Theme** | Web GUI supports theme switching |
| **Zero External Dependencies** | Core engine uses only Python standard library |
| **Service Deployment** | Ready-made scripts for Windows (NSSM) and Linux (systemd) |

### Supported Schedule Types

#### Recurring Schedule
Configure rules to be enabled or disabled during specific time windows on specific days.

- **Action: ENABLE in window** — Rule is enabled during the window, disabled outside.
- **Action: DISABLE in window** — Rule is disabled during the window, enabled outside.

#### One-Time Expiration
Rule will be automatically disabled when the expiration time is reached, and the schedule is removed.

---

## Operating Modes

### 1. Web GUI
A Flask-based single-page application with a responsive design.

```bash
python illumio_scheduler.py --gui --port 5002
```

### 2. CLI (Interactive)
A terminal-based interactive interface for browsing rulesets and managing schedules.

```bash
python illumio_scheduler.py
```

### 3. Daemon (Background Monitor)
Runs the schedule engine continuously, checking every 300 seconds (5 min) by default.

```bash
python illumio_scheduler.py --monitor
```

---

## Requirements

- **Python 3.7+**
- **Flask** (optional, only for Web GUI mode): `pip install flask`
- **Illumio PCE** with an API Key that has **Ruleset Provisioner** or **Global Organization Owner** permissions

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [User Manual](User_Manual_en.md) | Step-by-step operating instructions |
| [Architecture](Architecture_en.md) | Code structure, class design, and extension guide |
| [API Cookbook](API_Cookbook_en.md) | Python examples for direct Illumio API automation |
