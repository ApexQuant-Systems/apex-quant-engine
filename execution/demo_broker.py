import os
import sys
import asyncio
import time
import hmac
import hashlib
import urllib.request
import urllib.parse
import json

# Append workspace root directory for clean asset loading path access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class ApexDemoBroker:
    """
    🛰️ APEX EXECUTION INFRASTRUCTURE: STAGE G DEMO BROKER
    Handles isolated order routing lifecycle against the Testnet Sandbox.
    Strictly decoupled from live strategy signals.
    """
    def __init__(self, env_path: str = ".env", base_url: str = "https://testnet.binance.vision"):
        self.base_url = base_url
        self.api_key = ""
        self.secret_key = ""
        self._load_credentials(env_path)

    def _load_credentials(self, env_path: str):
        if not os.path.exists(env_path):
            return
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    if key == "BINANCE_API_KEY":
                        self.api_key = val
                    elif key == "BINANCE_SECRET_KEY":
                        self.secret_key = val

    def _sign_payload(self, query_string: str) -> str:
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def _get_server_time_ms(self) -> int:
        endpoint = f"{self.base_url}/api/v3/time"
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, urllib.request.urlopen, endpoint)
            return json.loads(response.read().decode("utf-8")).get("serverTime")
        except Exception:
            return int(time.time() * 1000)

    async def execute_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Dispatches an institutional MARKET order payload to the matching engine."""
        endpoint = f"{self.base_url}/api/v3/order"
        server_time = await self._get_server_time_ms()
        
        # Build the standardized order parameters
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": server_time,
            "recvWindow": 5000
        }
        
        query_string = urllib.parse.urlencode(params)
        signature = self._sign_payload(query_string)
        payload_data = f"{query_string}&signature={signature}".encode("utf-8")
        
        # Configure a strict POST execution state request
        req = urllib.request.Request(endpoint, data=payload_data, method="POST")
        req.add_header("X-MBX-APIKEY", self.api_key)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        print(f"⚡ Dispatching synthetic [MARKET {side.upper()}] order for {quantity} {symbol}...")
        start_time = time.perf_counter()
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            raw_response = json.loads(response.read().decode("utf-8"))
            latency = (time.perf_counter() - start_time) * 1000
            
            print(f"🟢 [EXECUTION ACK] Order processed by engine. Latency: {latency:.2f} ms")
            return raw_response
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            print(f"❌ [ENGINE REJECTION] Order refused by matching gateway: {err_msg}")
            return {}
        except Exception as e:
            print(f"❌ [CRITICAL CONNECTIVITY FAULT] Internal broker pipeline failure: {e}")
            return {}

async def run_synthetic_test():
    print("=====================================================================")
    print(" 🛰️  APEX EXECUTION ROUTER: TESTING DEMO ORDER LIFECYCLE (STAGE G)")
    print("=====================================================================")
    
    broker = ApexDemoBroker()
    
    # Fire Step 1 & 2: A small synthetic market BUY order for Bitcoin
    order_receipt = await broker.execute_market_order(symbol="BTCUSDT", side="BUY", quantity=0.01)
    
    if order_receipt:
        print("-" * 69)
        print("📋 RAW INTERFACE HANDSHAKE ACKNOWLEDGMENT RECEPTACLE:")
        print(f"  ├── Order ID     : {order_receipt.get('orderId')}")
        print(f"  ├── Client Client: {order_receipt.get('clientOrderId')}")
        print(f"  ├── Status Code  : {order_receipt.get('status')}")
        print(f"  ├── Executed Qty : {order_receipt.get('executedQty')}")
        print(f"  └── Cumulative Quote Qty: {order_receipt.get('cummulativeQuoteQty')}")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_synthetic_test())
