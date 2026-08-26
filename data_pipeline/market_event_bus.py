import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable

@dataclass(frozen=True)
class MarketTickEvent:
    timestamp: int
    symbol: str
    price: float
    volume: float

@dataclass(frozen=True)
class CanonicalCandleEvent:
    timestamp: int
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketEventBus:
    """
    🛰️ APEX PLATFORM PRIMITIVE: CENTRAL CHRONOLOGICAL EVENT ROUTER
    Provides a decoupled Pub-Sub registry for unified data transport.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {
            "tick": [],
            "candle": []
        }
        
    def subscribe(self, event_type: str, callback: Callable):
        """Register an infrastructure module to listen to specific standardized data streams."""
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)
            print(f"  └── [BUS] Subscribed callback function to topic: [{event_type}]")
            
    def publish(self, event_type: str, event_data):
        """Broadcast an incoming normalized event to all downstream active modules."""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    print(f"  ❌ [BUS CRITICAL] Callback failure on topic [{event_type}]: {e}")

    def normalize_binance_tick(self, symbol: str, raw_json_payload: str):
        """Converts raw exchange streaming tick data strings into immutable typed event frames."""
        try:
            data = json.loads(raw_json_payload)
            # Standard Binance Mini-Ticker Format Mapping
            normalized_event = MarketTickEvent(
                timestamp=int(data.get('E', 0)),
                symbol=symbol,
                price=float(data.get('c', 0.0)),
                volume=float(data.get('v', 0.0))
            )
            self.publish("tick", normalized_event)
        except Exception as e:
            print(f"  ⚠️ [BUS ERROR] Tick transformation rejected: {e}")

if __name__ == "__main__":
    print("=====================================================================")
    print(" 🛰️ APEX DATA PIPELINE: TESTING INITIAL EVENT BUS REGISTRY")
    print("=====================================================================")
    
    # Instantiate the bus component
    bus = MarketEventBus()
    
    # Mock subscriber modules simulating the Strategy and Database modules
    def mock_strategy_engine(event: MarketTickEvent):
        print(f"  ├── [STRATEGY CORE INGEST] Signal eval processed for {event.symbol} at ${event.price}")

    def mock_database_ledger(event: MarketTickEvent):
        print(f"  └── [SQL LEDGER LOG] Persisted row update: {asdict(event)}")
        
    # Wire the subscribers into the centralized hub
    bus.subscribe("tick", mock_strategy_engine)
    bus.subscribe("tick", mock_database_ledger)
    
    # Simulate a raw data packet hitting the system from a Binance stream connection
    mock_raw_binance_packet = '{"e":"24hrMiniTicker","E":1718222000000,"s":"BTCUSDT","c":"68250.50","v":"142.35"}'
    
    print("\n⚡ Ingesting raw network packet from exchange interface...")
    bus.normalize_binance_tick("BTCUSDT", mock_raw_binance_packet)
    print("=====================================================================")
