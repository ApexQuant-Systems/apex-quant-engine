import asyncio
import json
import time
import random
import sqlite3
import os

# --- CENTRAL PLATFORM TELEMETRY REGISTRY ---
SLO_METRICS = {
    "total_ingested": 0,
    "queue_peak_depth": 0,
    "db_sync_count": 0,
    "reconnect_attempts": 0,
    "max_processing_lag_ms": 0.0,
    "corrupt_dropped": 0
}

class ResilientLiveIngestor:
    """
    🛰️ APEX PLATFORM ENGINE: MODULE 6 LIVE INGESTOR PRIMITIVE
    Implements a decoupled Producer-Consumer pattern using an asynchronous queue
    to buffer real-time exchange streams from downstream storage operations.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db", max_queue_size: int = 5000):
        self.db_path = db_path
        self.event_queue = asyncio.Queue(maxsize=max_queue_size)
        self.is_running = True

    async def start_ingestion_pipeline(self):
        print("=====================================================================")
        print(" 🛰️ APEX PLATFORM: INITIALIZING RESILIENT LIVE DATA INGESTOR")
        print("=====================================================================")
        
        # Initialize background worker pool to consume the incoming network queue
        db_worker_task = asyncio.create_task(self._async_database_worker())
        telemetry_task = asyncio.create_task(self._live_telemetry_broadcaster())
        
        try:
            # Launch the central network socket supervisor
            await self._network_stream_supervisor()
        except asyncio.CancelledError:
            print("  ⚠️ Ingestion pipeline received manual cancellation shutdown signal.")
        finally:
            self.is_running = False
            await self.event_queue.join()
            db_worker_task.cancel()
            telemetry_task.cancel()
            print("=====================================================================")
            print("🏁 SHUTDOWN COMPLETE: PLATFORM INGESTION CHANNELS DISCONNECTED")

    async def _network_stream_supervisor(self):
        """Simulates an active, volatile network connection with automatic retry logic."""
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        while self.is_running:
            try:
                print("⚡ Connecting to live exchange stream gateway...")
                await asyncio.sleep(0.5) # Simulate connection handshake latency
                print("🟢 Stream established. Streaming high-density asset data frames...")
                
                # Run ingestion until a random simulated network disconnect occurs
                for session_tick in range(500):
                    SLO_METRICS["total_ingested"] += 1
                    
                    # Track operational queue peak depths to measure network backpressure
                    current_depth = self.event_queue.qsize()
                    if current_depth > SLO_METRICS["queue_peak_depth"]:
                        SLO_METRICS["queue_peak_depth"] = current_depth
                        
                    # Handle structural queue overflows gracefully
                    if self.event_queue.full():
                        print("  ❌ [BUFFER OVERFLOW] Queue ceiling reached. Dropping packet.")
                        SLO_METRICS["corrupt_dropped"] += 1
                        continue

                    # Mock a live exchange network transmission packet string
                    mock_packet = {
                        "timestamp": int(time.time() * 1000),
                        "symbol": random.choice(symbols),
                        "price": round(random.uniform(20.0, 65000.0), 2),
                        "volume": round(random.uniform(0.1, 80.0), 4)
                    }
                    
                    # Push raw string into the asynchronous backpressure buffer queue
                    await self.event_queue.put(json.dumps(mock_packet))
                    
                    # Simulate rapid high-frequency data burst intervals (1ms to 15ms)
                    await asyncio.sleep(random.uniform(0.001, 0.015))
                    
                # Force a connection drop simulation to test state recovery logic
                raise ConnectionError("Network socket heartbeat timeout drop.")
                
            except (ConnectionError, Exception) as e:
                SLO_METRICS["reconnect_attempts"] += 1
                print(f"  ⚠️ [CONNECTION LOST] {e}")
                print(f"  └── Triggering automatic cooling cycle. Reconnect attempt #{SLO_METRICS['reconnect_attempts']} imminent...")
                await asyncio.sleep(2.0) # Backoff recovery interval

    async def _async_database_worker(self):
        """Decoupled background consumer pool. Manages persistent storage operations."""
        while self.is_running:
            raw_payload = await self.event_queue.get()
            start_latency_time = time.perf_counter()
            
            try:
                data = json.loads(raw_payload)
                
                # Log incoming normalized frames straight into our SQLite database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO market_ticks (timestamp, symbol, price, volume)
                    VALUES (?, ?, ?, ?)
                """, (data["timestamp"], data["symbol"], data["price"], data["volume"]))
                conn.commit()
                conn.close()
                
                SLO_METRICS["db_sync_count"] += 1
            except Exception as e:
                SLO_METRICS["corrupt_dropped"] += 1
            finally:
                self.event_queue.task_done()
                
            # Compute operational processing lag from network arrival to disk storage
            processing_lag = (time.perf_counter() - start_latency_time) * 1000
            if processing_lag > SLO_METRICS["max_processing_lag_ms"]:
                SLO_METRICS["max_processing_lag_ms"] = processing_lag

    async def _live_telemetry_broadcaster(self):
        """Continuously prints system performance data without blocking execution threads."""
        while self.is_running:
            await asyncio.sleep(3.0)
            print("-" * 69)
            print(f"📡 REAL-TIME PLATFORM TELEMETRY REPORT:")
            print(f"  ├── Packets Ingested    : {SLO_METRICS['total_ingested']}")
            print(f"  ├── Database Commits    : {SLO_METRICS['db_sync_count']}")
            print(f"  ├── Buffer Queue Backlog: {self.event_queue.qsize()} events (Peak: {SLO_METRICS['queue_peak_depth']})")
            print(f"  ├── Network Reconnects  : {SLO_METRICS['reconnect_attempts']}")
            print(f"  └── Max Pipeline Lag    : {SLO_METRICS['max_processing_lag_ms']:.2f} ms")
            print("-" * 69)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    ingestor = ResilientLiveIngestor()
    try:
        # Run the ingestion session loop
        asyncio.run(asyncio.wait_for(ingestor.start_ingestion_pipeline(), timeout=12.0))
    except asyncio.TimeoutError:
        print("\n🟢 [SOAK TEST WINDOW COMPLETE] Ingestor session concluded safely.")
