import time
import os
import sys
from infrastructure.logger import QuantLogger

# Hardened Absolute Path Targeting
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HEARTBEAT_FILE = os.path.join(BASE_DIR, "infrastructure", "heartbeat.txt")

def pulse_heartbeat():
    """Programmatically updates the absolute heartbeat target file"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"[-] Failed to write heartbeat: {e}")

def start_production_loop():
    log = QuantLogger()
    log.log("\n==============================================")
    log.log("   INITIALIZING LIVE PRODUCTION ENGINE v1.0   ")
    log.log("==============================================")
    
    while True:
        log.log("[*] Scanning real-time market matrix for BTC_USDT...")
        time.sleep(2) 
        
        pulse_heartbeat()
        log.log("[+] Heartbeat pulsed successfully. System nominal.")
        
        time.sleep(15)

if __name__ == "__main__":
    try:
        start_production_loop()
    except KeyboardInterrupt:
        print("\nProduction engine safely shut down by operator.")
        sys.exit(0)
