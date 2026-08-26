import asyncio
import time
import urllib.request
import json

class ReadOnlyExecutionGate:
    """
    🛰️ APEX EXECUTION LAYER: SPRINT 4 INITIAL CONNECTIVITY GATE
    Handles read-only network handshakes against live exchange endpoints
    without any order execution pathways.
    """
    def __init__(self, base_url: str = "https://api.binance.com"):
        self.base_url = base_url

    async def verify_exchange_heartbeat(self) -> bool:
        """Pings the live exchange endpoint to measure real-world network latency."""
        endpoint = f"{self.base_url}/api/v3/ping"
        start_time = time.perf_counter()
        
        try:
            # Execute a non-blocking network request using a background thread execution pool
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, urllib.request.urlopen, endpoint)
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            print(f"  ├── [NETWORK PING SUCCESS] Connected to live exchange gateway.")
            print(f"  └── Real-World Network Round-Trip Latency: {latency_ms:.2f} ms")
            return True
        except Exception as e:
            print(f"  ❌ [NETWORK CRITICAL] Handshake rejected by exchange server: {e}")
            return False

    async def fetch_public_ticker(self, symbol: str):
        """Fetches live market price information to test JSON string ingestion formatting."""
        endpoint = f"{self.base_url}/api/v3/ticker/price?symbol={symbol}"
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, endpoint)
            raw_data = response.read().decode('utf-8')
            parsed_json = json.loads(raw_data)
            
            print(f"  ├── [DATA FETCH SUCCESS] Symbol: {parsed_json.get('symbol')}")
            print(f"  └── Live Spot Reference Price: ${float(parsed_json.get('price', 0.0)):,.2f}")
        except Exception as e:
            print(f"  ❌ [DATA FETCH ERROR] Failed to parse ticker: {e}")

async def main():
    print("=====================================================================")
    print(" 🛰️ APEX EXECUTION: TESTING LIVE READ-ONLY GATEWAYS (SPRINT 4)")
    print("=====================================================================")
    
    gate = ReadOnlyExecutionGate()
    
    print("⚡ Initiating active live network heartbeat ping...")
    is_online = await gate.verify_exchange_heartbeat()
    
    if is_online:
        print("\n⚡ Requesting real-time public ticker frame for BTCUSDT...")
        await gate.fetch_public_ticker("BTCUSDT")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(main())
