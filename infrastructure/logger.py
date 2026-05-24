import os
import time

def check_system():
    heartbeat_file = "infrastructure/heartbeat.txt"
    while True:
        if os.path.exists(heartbeat_file):
            last_update = os.path.getmtime(heartbeat_file)
            if time.time() - last_update > 60: # System stale
                print("ALERT: HEARTBEAT STALE. RESTARTING ENGINE...")
                # Add logic here to kill process and restart main.py
        else:
            print("ALERT: NO HEARTBEAT DETECTED.")
        time.sleep(10)

if __name__ == "__main__":
    check_system()
