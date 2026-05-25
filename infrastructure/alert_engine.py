import sys
from datetime import datetime

class AlertEngine:
    def __init__(self):
        # This will hold Webhook URLs for Discord/Telegram later
        self.enabled = True

    def send_emergency(self, component, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = f"🚨 [CRITICAL SYSTEM ALERT] | {timestamp} | Component: {component} -> {message}"
        
        # Console Routing
        print(payload)
        
        # PLACEHOLDER FOR LIVE WEBHOOK IN PHASE 10
        # requests.post(self.webhook_url, json={"content": payload})
        return payload

if __name__ == "__main__":
    alerts = AlertEngine()
    alerts.send_emergency("WatchdogCore", "Test transmission. Telemetry pipeline nominal.")
