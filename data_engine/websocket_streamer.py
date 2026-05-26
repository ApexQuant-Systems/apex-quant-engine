import asyncio
import json
import os
import sys
from datetime import datetime

# Path correction to expose root directory to the Python execution context
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

class LiveMarketStreamer:
    def __init__(self, symbol="btcusdt"):
        self.symbol = symbol.lower()
        self.url = f"wss://stream.binance.com:9443/ws/{self.symbol}@ticker"
        self.running = True

    async def connect_stream(self):
        import websockets
        print(f"[{datetime.now()}] Connecting to institutional stream matrix: {self.url}")
        
        while self.running:
            try:
                async with websockets.connect(self.url) as ws:
                    print(f"[{datetime.now()}] [CONNECTED] Raw tick ingestion pipeline open.")
                    
                    while self.running:
                        raw_data = await ws.recv()
                        data = json.loads(raw_data)
                        
                        current_price = data.get('c') # Current close price
                        volume = data.get('v')        # 24h accumulated volume
                        
                        if current_price:
                            print(f"[{datetime.now()}] [TICK] BTC_USDT -> ${float(current_price):,.2f} | 24h Vol: {float(volume):,.2f}")
                            
            except Exception as e:
                print(f"[-] Stream disconnection detected: {e}")
                print("[*] Reconnecting transport pipeline in 5 seconds...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    streamer = LiveMarketStreamer()
    try:
        asyncio.run(streamer.connect_stream())
    except KeyboardInterrupt:
        print("\nIngestion pipeline safely disconnected by operator.")
        sys.exit(0)
