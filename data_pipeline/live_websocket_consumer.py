import os
import sys

# 🛰️ APEX PATH BOILERPLATE: Append root directory to Python path context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import json
import time
import websockets
from data_pipeline.market_event_bus import MarketTickEvent

class HighSpeedWebSocketConsumer:
    """
    🛰️ APEX STREAM INGESTION: STAGE 2 PUBLIC STREAM CONSUMER
    Opens a persistent, low-overhead WebSocket stream channel to feed
    normalized exchange tick events directly into the hardened event bus.
    """
    def __init__(self, target_symbols: list, event_bus_reference):
        self.symbols = [s.lower() for s in target_symbols]
        self.bus = event_bus_reference
        self.is_active = True
        
        # Construct the unified stream parameter string
        stream_paths = "/".join([f"{sym}@miniTicker" for sym in self.symbols])
        self.stream_url = f"wss://stream.binance.com:9443/stream?streams={stream_paths}"

    async def launch_stream_listener(self):
        print("=====================================================================")
        print(" 🛰️ APEX INFRASTRUCTURE: STREAMING LIVE EXCHANGE DATA CHANNELS")
        print("=====================================================================")
        print(f"📡 Target Ingest Streams: {self.symbols}")
        print(f"🔗 Gateway Socket: {self.stream_url}\n")
        
        reconnect_delay = 1.0
        
        while self.is_active:
            try:
                async with websockets.connect(self.stream_url) as ws:
                    print("🟢 [STREAM ONLINE] Asynchronous websocket channel established.")
                    reconnect_delay = 1.0 # Reset recovery backoff on successful handshake
                    
                    while self.is_active:
                        raw_payload = await ws.recv()
                        arrival_timestamp = int(time.time() * 1000)
                        
                        # Delegate network processing instantly to a non-blocking background task
                        asyncio.create_task(self._process_stream_frame(raw_payload, arrival_timestamp))
                        
            except (websockets.exceptions.ConnectionClosed, Exception) as e:
                print(f"  ⚠️ [STREAM DISCONNECT] Network socket drop detected: {e}")
                print(f"  └── Re-establishing stream connection loop in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30.0) # Bounded exponential backoff

    async def _process_stream_frame(self, raw_data: str, arrival_time: int):
        """Transforms raw stream JSON updates into immutable internal market tick formats."""
        try:
            payload = json.loads(raw_data)
            stream_name = payload.get("stream", "")
            data_block = payload.get("data", {})
            
            # Extract standard Binance mini-ticker properties
            event_time = int(data_block.get("E", arrival_time))
            symbol = data_block.get("s", "UNKNOWN")
            close_price = float(data_block.get("c", 0.0))
            volume = float(data_block.get("v", 0.0))
            
            # Compute real-world transmission lag across the network wire
            wire_transit_lag = arrival_time - event_time
            
            print(f"  ├── [TICK INGESTED] {symbol:<9} | Price: ${close_price:<10,.2f} | Wire Transit Lag: {wire_transit_lag} ms")
            
            # Reconstruct the target frame object to feed your storage sinks
            normalized_tick = MarketTickEvent(
                timestamp=event_time,
                symbol=symbol,
                price=close_price,
                volume=volume
            )
            
            # Broadcast the clean data packet down the pipeline
            await self.bus.publish("tick", normalized_tick)
            
        except Exception as e:
            print(f"  ❌ [PARSING FAULT] Stream payload rejected: {e}")

if __name__ == "__main__":
    from research.operational_hardening import ProductionEventBus
    
    async def mock_strategy_listener(event):
        pass # Passive subscriber placeholder
        
    async def start_demo_session():
        # Spin up your production event bus instance
        apex_bus = ProductionEventBus()
        apex_bus.register_subscriber("strategy", "CRITICAL_BACKPRESSURE", mock_strategy_listener)
        
        consumer = HighSpeedWebSocketConsumer(target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"], event_bus_reference=apex_bus)
        
        # Run a brief 15-second live session to verify data stream performance
        try:
            await asyncio.wait_for(consumer.launch_stream_listener(), timeout=15.0)
        except asyncio.TimeoutError:
            print("\n=====================================================================")
            print("🟢 [STAGE 2 WINDOW COMPLETE] Live ingest window closed safely.")
            print("=====================================================================")

    asyncio.run(start_demo_session())
