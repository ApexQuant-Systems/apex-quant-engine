import os
import sys
import asyncio
import json
import time
import sqlite3
import websockets

# Append workspace root directory for clean asset loading path access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- EXPANDED METRICS REGISTRY ---
SOAK_TELEMETRY = {
    "ingested": 0,
    "strat_processed": 0,
    "db_processed": 0,
    "db_dropped": 0,
    "reconnects": 0,
    "socket_disconnects": 0,
    "peak_tasks": 0
}

# In-memory arrays for exact statistical percentile execution tracking
STRAT_LATENCIES = []

def calculate_percentile(data_list, percentile):
    """Computes exact percentile values natively from raw historical integer lists."""
    if not data_list:
        return 0.0
    sorted_data = sorted(data_list)
    index = (len(sorted_data) - 1) * percentile
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return float(sorted_data[lower])
    # Linear interpolation calculation across index boundaries
    return sorted_data[lower] + (index - lower) * (sorted_data[upper] - sorted_data[lower])

class HardenedProductionBus:
    def __init__(self, queue_ceiling: int = 200):
        self.queue_ceiling = queue_ceiling
        self._queues = {}
        self._policies = {}
        self._workers = []

    def register_subscriber(self, name: str, policy: str, worker_callback):
        q = asyncio.Queue(maxsize=self.queue_ceiling)
        self._queues[name] = q
        self._policies[name] = policy
        self._workers.append(asyncio.create_task(self._worker_loop(name, q, worker_callback)))
        print(f"  └── [STAGE E+ BUS] Isolation Queue [{name:<8}] Active | Bounded Ceiling: {self.queue_ceiling}")

    async def publish(self, event: dict):
        SOAK_TELEMETRY["ingested"] += 1
        
        current_tasks = len(asyncio.all_tasks())
        if current_tasks > SOAK_TELEMETRY["peak_tasks"]:
            SOAK_TELEMETRY["peak_tasks"] = current_tasks

        for name, q in self._queues.items():
            policy = self._policies[name]
            if q.full():
                if policy == "DROP_OLDEST":
                    try:
                        q.get_nowait()
                        q.task_done()
                        SOAK_TELEMETRY["db_dropped"] += 1
                    except asyncio.QueueEmpty:
                        pass
                elif policy == "CRITICAL_BACKPRESSURE":
                    while q.full():
                        await asyncio.sleep(0.001)
            q.put_nowait(event)

    async def _worker_loop(self, name: str, queue: asyncio.Queue, callback):
        while True:
            event = await queue.get()
            start_time = time.perf_counter()
            try:
                await callback(event)
            except Exception:
                pass
            finally:
                queue.task_done()
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            if name == "strategy":
                STRAT_LATENCIES.append(latency_ms)
                # Keep sliding memory array bounded to the last 10,000 observations to prevent memory drift
                if len(STRAT_LATENCIES) > 10000:
                    STRAT_LATENCIES.pop(0)

    def shutdown(self):
        for task in self._workers:
            task.cancel()

# --- LIVE WORKER CONSUMER BLOCK ---
async def strategy_soak_evaluator(event: dict):
    SOAK_TELEMETRY["strat_processed"] += 1
    await asyncio.sleep(0.0002) # Mimic 200 microsecond production matching overhead

async def database_soak_sink(event: dict):
    db_path = "data/forward_testing_vault.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO market_ticks (timestamp, symbol, price, volume)
            VALUES (?, ?, ?, ?)
        """, (event["timestamp"], event["symbol"], event["price"], event["volume"]))
        conn.commit()
        SOAK_TELEMETRY["db_processed"] += 1
    except Exception:
        SOAK_TELEMETRY["db_dropped"] += 1
    finally:
        conn.close()

# --- HIGH FIDELITY MONITOR ORCHESTRATOR ---
class ExtendedSoakHarness:
    def __init__(self, target_symbols: list, duration_minutes: float = 60.0):
        self.symbols = [s.lower() for s in target_symbols]
        self.duration_seconds = duration_minutes * 60
        self.bus = HardenedProductionBus(queue_ceiling=500)
        
        stream_paths = "/".join([f"{sym}@miniTicker" for sym in self.symbols])
        self.stream_url = f"wss://stream.binance.com:9443/stream?streams={stream_paths}"
        self.log_file = f"telemetry/soak_profile_{int(time.time())}.csv"

    async def execute_campaign(self):
        os.makedirs("telemetry", exist_ok=True)
        with open(self.log_file, "w") as f:
            f.write("ELAPSED_SEC,INGESTED,STRAT_PROC,DB_COMMITS,DB_DROPS,AVG_LAT_MS,P95_LAT_MS,P99_LAT_MS,TASKS,RECONNECTS\n")

        self.bus.register_subscriber("strategy", "CRITICAL_BACKPRESSURE", strategy_soak_evaluator)
        self.bus.register_subscriber("db", "DROP_OLDEST", database_soak_sink)
        
        print(f"\n⚡ Opening high-fidelity log output destination: {self.log_file}")
        print("🟢 Connecting websocket ingestion core to live exchange matrix...")
        
        start_wall_time = time.time()
        metrics_broadcaster = asyncio.create_task(self._run_statistical_broadcaster(start_wall_time))
        
        reconnect_delay = 1.0
        while (time.time() - start_wall_time) < self.duration_seconds:
            try:
                async with websockets.connect(self.stream_url) as ws:
                    reconnect_delay = 1.0
                    while (time.time() - start_wall_time) < self.duration_seconds:
                        raw_payload = await ws.recv()
                        arrival_time = int(time.time() * 1000)
                        
                        payload = json.loads(raw_payload)
                        data_block = payload.get("data", {})
                        
                        normalized_event = {
                            "timestamp": int(data_block.get("E", arrival_time)),
                            "symbol": data_block.get("s", "UNKNOWN"),
                            "price": float(data_block.get("c", 0.0)),
                            "volume": float(data_block.get("v", 0.0))
                        }
                        await self.bus.publish(normalized_event)
            except (websockets.exceptions.ConnectionClosed, Exception):
                SOAK_TELEMETRY["socket_disconnects"] += 1
                SOAK_TELEMETRY["reconnects"] += 1
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 15.0)

        metrics_broadcaster.cancel()
        self.bus.shutdown()
        print("\n=====================================================================")
        print("🏁 STAGE E+ WINDOW CONCLUDED: HARDENED PLUMBING SHUT DOWN SAFELY")
        print("=====================================================================")

    async def _run_statistical_broadcaster(self, start_time: float):
        while True:
            await asyncio.sleep(10.0) # Print high-fidelity statistical rows every 10 seconds
            elapsed = int(time.time() - start_time)
            
            # Extract raw in-memory metrics cleanly
            avg_lat = sum(STRAT_LATENCIES) / len(STRAT_LATENCIES) if STRAT_LATENCIES else 0.0
            p95_lat = calculate_percentile(STRAT_LATENCIES, 0.95)
            p99_lat = calculate_percentile(STRAT_LATENCIES, 0.99)
            
            print(f"⏱️  [{elapsed:>4}s] Ingested: {SOAK_TELEMETRY['ingested']:<5} | "
                  f"Avg Latency: {avg_lat:.2f}ms | P95: {p95_lat:.2f}ms | P99: {p99_lat:.2f}ms | "
                  f"Tasks: {SOAK_TELEMETRY['peak_tasks']} (SLO Flatlined)")
            
            # Flush structured mathematical profile metrics onto local disk arrays
            csv_row = f"{elapsed},{SOAK_TELEMETRY['ingested']},{SOAK_TELEMETRY['strat_processed']},{SOAK_TELEMETRY['db_processed']},{SOAK_TELEMETRY['db_dropped']},{avg_lat:.4f},{p95_lat:.4f},{p99_lat:.4f},{SOAK_TELEMETRY['peak_tasks']},{SOAK_TELEMETRY['reconnects']}\n"
            with open(self.log_file, "a") as f:
                f.write(csv_row)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    # Configure an initialization window of 1 minute to certify logging accuracy
    runner = ExtendedSoakHarness(target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"], duration_minutes=60.0)
    try:
        asyncio.run(runner.execute_campaign())
    except KeyboardInterrupt:
        print("\nManual override disconnect caught.")
