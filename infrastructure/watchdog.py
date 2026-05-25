import os
import time
import sys
from datetime import datetime

# Establish deterministic root path matrix
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from infrastructure.alert_engine import AlertEngine

# Hardened Absolute Path Targeting
HEARTBEAT_FILE = os.path.join(BASE_DIR, "infrastructure", "heartbeat.txt")
STALE_THRESHOLD_SECS = 60

def monitor_system():
    alerts = AlertEngine()
    print(f"[{datetime.now()}] >>> WATCHDOG CORE ONLINE: Monitoring system pulse...")
    
    while True:
        if not os.path.exists(HEARTBEAT_FILE):
            alerts.send_emergency("WatchdogCore", "Heartbeat file missing from disk entirely!")
            time.sleep(10)
            continue
            
        last_heartbeat_time = os.path.getmtime(HEARTBEAT_FILE)
        seconds_since_heartbeat = time.time() - last_heartbeat_time
        
        if seconds_since_heartbeat > STALE_THRESHOLD_SECS:
            error_msg = f"SYSTEM STALE FOR {int(seconds_since_heartbeat)}s. Core Engine frozen or disconnected."
            alerts.send_emergency("AlphaEngine_V1", error_msg)
        else:
            # Operational Upgrade: Visual confirmation of system health
            print(f"[{datetime.now()}] [OK] Pulse nominal. Delta: {int(seconds_since_heartbeat)}s.")
            
        time.sleep(10)

if __name__ == "__main__":
    try:
        monitor_system()
    except KeyboardInterrupt:
        print("\nWatchdog safely terminated by operator.")
        sys.exit(0)
