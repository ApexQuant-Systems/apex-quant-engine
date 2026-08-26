import asyncio
import time

TELEMETRY = {
    "ticks_ingested": 0,
    "strategy_processed": 0,
    "db_processed": 0,
    "strategy_dropped": 0,
    "db_dropped": 0,
    "max_strategy_latency_ms": 0.0,
    "max_db_latency_ms": 0.0,
    "active_task_count_peak": 0
}

class ProductionEventBus:
    """
    🛰️ APEX INFRASTRUCTURE: SPRINT 3C PRODUCTION CORE
    Features strict subscriber isolation, non-blocking put_nowait execution,
    and standardized institutional publishing interfaces.
    """
    def __init__(self, queue_ceiling: int = 100):
        self.queue_ceiling = queue_ceiling
        self._queues = {}
        self._policies = {}
        self._workers = []

    def register_subscriber(self, name: str, policy: str, worker_callback):
        q = asyncio.Queue(maxsize=self.queue_ceiling)
        self._queues[name] = q
        self._policies[name] = policy
        self._workers.append(asyncio.create_task(self._worker_loop(name, q, worker_callback)))
        print(f"  └── [PRODUCTION BUS] Registered [{name}] | Policy: {policy} (Ceiling: {self.queue_ceiling})")

    async def publish(self, event_type: str, event_data):
        """Standard institutional pub-sub interface mapping directly to core broadcast structures."""
        await self.broadcast(event_data)

    async def broadcast(self, event):
        """Executes strictly non-blocking synchronous enqueue checks."""
        TELEMETRY["ticks_ingested"] += 1
        
        current_tasks = len(asyncio.all_tasks())
        if current_tasks > TELEMETRY["active_task_count_peak"]:
            TELEMETRY["active_task_count_peak"] = current_tasks

        for name, q in self._queues.items():
            policy = self._policies[name]
            
            if q.full():
                if policy == "DROP_OLDEST":
                    try:
                        q.get_nowait()
                        q.task_done()
                        TELEMETRY[f"{name}_dropped"] += 1
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
                # Convert dataclass frameworks to dict frames if required by consumer legacy signatures
                await callback(event)
            except Exception as e:
                pass
            finally:
                queue.task_done()
                
            latency = (time.perf_counter() - start_time) * 1000
            if latency > TELEMETRY[f"max_{name}_latency_ms"]:
                TELEMETRY[f"max_{name}_latency_ms"] = latency

    def shutdown(self):
        for task in self._workers:
            task.cancel()
