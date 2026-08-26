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

class ApexProductionBroker:
    """
    🛰️ APEX EXECUTION INFRASTRUCTURE: STAGE G LEVEL 3
    Features explicit HTTPError body extraction to expose engine parameter rejections.
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

    async def submit_resting_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> dict:
        """Submits a passive resting LIMIT order with diagnostic error extraction."""
        endpoint = f"{self.base_url}/api/v3/order"
        server_time = await self._get_server_time_ms()
        
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": price,
            "timestamp": server_time,
            "recvWindow": 5000
        }
        
        query_string = urllib.parse.urlencode(params)
        signature = self._sign_payload(query_string)
        payload_data = f"{query_string}&signature={signature}".encode("utf-8")
        
        req = urllib.request.Request(endpoint, data=payload_data, method="POST")
        req.add_header("X-MBX-APIKEY", self.api_key)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"  ❌ [ENGINE LIMIT REJECTION] Server returned 400: {err_body}")
            return {}
        except Exception as e:
            print(f"  ❌ [PLACEMENT EXCEPTION] Internal plumbing fault: {e}")
            return {}

    async def cancel_active_order(self, symbol: str, order_id: int) -> dict:
        endpoint = f"{self.base_url}/api/v3/order"
        server_time = await self._get_server_time_ms()
        
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id,
            "timestamp": server_time,
            "recvWindow": 5000
        }
        
        query_string = urllib.parse.urlencode(params)
        signature = self._sign_payload(query_string)
        full_url = f"{endpoint}?{query_string}&signature={signature}"
        
        req = urllib.request.Request(full_url, method="DELETE")
        req.add_header("X-MBX-APIKEY", self.api_key)
        
        print(f"⚡ Requesting cancellation loop for Order ID: {order_id}...")
        start_time = time.perf_counter()
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            raw_response = json.loads(response.read().decode("utf-8"))
            latency = (time.perf_counter() - start_time) * 1000
            
            print(f"🟢 [CANCEL ACK] Order liquidated cleanly from book. Latency: {latency:.2f} ms")
            return raw_response
        except Exception as e:
            print(f"  ❌ [CANCEL REFUSED] Exchange rejected execution removal payload: {e}")
            return {}

async def execute_lifecycle_sequence():
    print("=====================================================================")
    print(" 🛰️  APEX EXECUTION CORE: DIAGNOSING LIMIT LIFECYCLE (STAGE G)")
    print("=====================================================================")
    
    broker = ApexProductionBroker()
    
    # Adjusted price from $30k to $60k to sit within valid percentage filter distance rules
    target_price = 60000.0
    print(f"⚡ Dispatching resting passive ${target_price:,.2f} LIMIT BUY order for BTCUSDT...")
    placement = await broker.submit_resting_limit_order(symbol="BTCUSDT", side="BUY", quantity=0.01, price=target_price)
    
    order_id = placement.get("orderId")
    if order_id:
        print(f"🟢 [PLACEMENT ACK] Open Order Confirmed | ID: {order_id} | Status: {placement.get('status')}")
        print("-" * 69)
        
        await asyncio.sleep(2.0)
        await broker.cancel_active_order(symbol="BTCUSDT", order_id=order_id)
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(execute_lifecycle_sequence())
