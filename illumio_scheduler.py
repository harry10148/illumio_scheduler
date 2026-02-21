import os
import sys
import time

# ==========================================
# File Paths & Core Init
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "rule_schedules.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

from src.core import ConfigManager, ScheduleDB, PCEClient, ScheduleEngine

def init_core():
    cfg = ConfigManager(CONFIG_FILE)
    db = ScheduleDB(DB_FILE)
    pce = PCEClient(cfg)
    engine = ScheduleEngine(db, pce)
    return {'cfg': cfg, 'db': db, 'pce': pce, 'engine': engine}

# ==========================================
# Application Entry Point
# ==========================================
if __name__ == "__main__":
    core_system = init_core()

    if "--monitor" in sys.argv:
        print("[*] Service Started (Daemon mode).")
        # Load check interval from env or default to 300s
        interval = int(os.environ.get("ILLUMIO_CHECK_INTERVAL", 300))
        while True:
            try:
                core_system['engine'].check(silent=True)
            except Exception as e:
                import traceback
                print(f"[DAEMON ERROR] {e}")
                traceback.print_exc()
            time.sleep(interval)

    elif "--gui" in sys.argv:
        try:
            from src.gui_ui import launch_gui
            launch_gui(core_system)
        except ImportError:
            print("[!] Web GUI requires Flask. Install with:")
            print("      pip install flask")
            print("    CLI mode works without Flask.")

    else:
        # Default to CLI mode (backward compatibility)
        from src.cli_ui import CLI
        cli_app = CLI(core_system)
        cli_app.run(core_system=core_system)
