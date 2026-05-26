import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

class LiveCandleBuilder:
    def __init__(self):
        self.url = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
        self.current_candle = None
        self.candle_duration = timedelta(minutes=1)
        print(f"[{datetime.now()}] Candle Aggregation Engine Initialized [Interval: 1M]")

    def init_candle(self, price, volume, timestamp):
        # Round down to the nearest clean minute boundary
        start_time = timestamp.replace(second=0, microsecond=0)
        return {
            "start_time": start_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 0.0
        }

    async def start_aggregation(self):
        import websockets
        async with websockets.connect(self.url) as ws:
            print(f"[{datetime.now()}] [CONNECTED] Aggregation pipes open. Building bars...")
            
            while True:
                raw_data = await ws.recv()
                data = json.loads(raw_data)
                
                price = float(data.get('c', 0))
                tick_time = datetime.fromtimestamp(data.get('E', 0) / 1000.0)
                
                if not self.current_candle:
                    self.current_candle = self.init_candle(price, price, tick_time)
                
                # Check if the tick belongs to a new minute block
                if tick_time >= self.current_candle["start_time"] + self.candle_duration:
                    # Freeze and emit completed candle
                    c = self.current_candle
                    print(f"\n⚡ [CANDLE CLOSED] | {c['start_time'].strftime('%H:%M:%S')} | O: ${c['open']:.2f} | H: ${c['high']:.2f} | L: ${c['low']:.2f} | C: ${c['close']:.2f}\n")
                    
                    # Cycle to the next structural candle block
                    self.current_candle = self.init_candle(price, price, tick_time)
                else:
                    # Update active candle metrics in real-time
                    self.current_candle["high"] = max(self.current_candle["high"], price)
                    self.current_candle["low"] = min(self.current_candle["low"], price)
                    self.current_candle["close"] = price
                    
                    # Print active telemetry pulse to screen
                    sys.stdout.write(f"\rBuilding Candle [{self.current_candle['start_time'].strftime('%H:%M:%S')}] Active Price: ${price:,.2f} | High: ${self.current_candle['high']:.2f} | Low: ${self.current_candle['low']:.2f}")
                    sys.stdout.flush()

if __name__ == "__main__":
    builder = LiveCandleBuilder()
    try:
        asyncio.run(builder.start_aggregation())
    except KeyboardInterrupt:
        print("\nAggregator safely shutdown by operator.")
        sys.exit(0)
