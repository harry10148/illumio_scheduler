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
    cfg.load()
    
    import src.i18n as i18n
    i18n.set_lang(cfg.config.get('lang', 'en'))

    db = ScheduleDB(DB_FILE)
    pce = PCEClient(cfg)
    engine = ScheduleEngine(db, pce)
    return {'cfg': cfg, 'db': db, 'pce': pce, 'engine': engine}

def get_port():
    """Parse --port <N> from sys.argv, default 5000"""
    for i, arg in enumerate(sys.argv):
        if arg == '--port' and i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                print(f"[!] Invalid port: {sys.argv[i + 1]}, using default 5000")
    return 5000

# ==========================================
# Application Entry Point
# ==========================================
if __name__ == "__main__":
    core_system = init_core()
    port = get_port()

    if "--monitor" in sys.argv:
        print(f"[*] Service Started (Daemon mode).")
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
            launch_gui(core_system, port=port)
        except ImportError:
            print("[!] Web GUI requires Flask. Install with:")
            print("      pip install flask")
            print("    CLI mode works without Flask.")

    else:
        # Default to CLI mode (backward compatibility)
        from src.cli_ui import CLI
        cli_app = CLI(core_system)
        cli_app.run(core_system=core_system)
