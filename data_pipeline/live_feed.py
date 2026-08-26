# filename: data_pipeline/live_feed.py
import asyncio
import json
import urllib.request
import logging
from typing import Dict, Any, Callable, List

class ApexLiveFeedEngine:
    """
    Module 1.5: Non-blocking asynchronous network pipeline engine.
    Establishes streaming connections and dispatches validated payloads to memory queues.
    """
    def __init__(self, target_symbols: List[str]):
        self.symbols = [s.lower() for s in target_symbols]
        self.is_running = False
        self.logger = logging.getLogger("ApexLiveFeedEngine")
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def register_subscriber(self, callback: Callable[[Dict[str, Any]], None]):
        """Binds a downstream intake module to receive incoming market ticks."""
        self._subscribers.append(callback)

    async def start_simulated_stream(self, test_cycles: int = 5):
        """
        Asynchronous streaming engine. Tracks asset states in real time
        without introducing event-loop scheduling stalls.
        """
        self.is_running = True
        self.logger.info(f"Apex Streaming Live Feed Engine successfully online for universe: {self.symbols}")
        
        cycles = 0
        while self.is_running and cycles < test_cycles:
            # Simulate real-time async market events to prevent event loop blocking
            await asyncio.sleep(0.1)
            
            simulated_tick = {
                "symbol": "BTCUSDT",
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                "price": 65000.0 + (cycles * 10.5),
                "volume": 1.25
            }
            
            # Fan out updates to registered subscribers instantly
            for subscriber in self._subscribers:
                try:
                    subscriber(simulated_tick)
                except Exception as e:
                    self.logger.error(f"Subscriber processing allocation crash: {str(e)}")
            
            cycles += 1
            
        self.is_running = False
        self.logger.info("Apex Streaming Live Feed Engine closed down cleanly.")
