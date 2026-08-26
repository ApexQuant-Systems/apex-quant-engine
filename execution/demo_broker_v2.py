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
    🛰️ APEX EXECUTION INFRASTRUCTURE: STAGE G LEVEL 2
    Implements advanced order lifecycle management including limit placement,
    state interrogation, and execution cancellation loops.
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
        """Submits a passive resting LIMIT order into the order book database."""
        endpoint = f"{self.base_url}/api/v3/order"
        server_time = await self._get_server_time_ms()
        
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC", # Good 'Til Canceled core strategy requirement
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
        except Exception as e:
            print(f"  ❌ [PLACEMENT EXCEPTION] Failed to place limit bounds: {e}")
            return {}

    async def cancel_active_order(self, symbol: str, order_id: int) -> dict:
        """Issues a cryptographic DELETE instruction to cleanly wipe a resting order."""
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
        
        # Build the final request URL string with properties signed cleanly
        full_url = f"{endpoint}?{query_string}&signature={signature}"
        
        # Map explicitly to the DELETE method mapping schema
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
    print(" 🛰️  APEX EXECUTION CORE: VERIFYING LIMIT & CANCELLATION LIFECYCLES")
    print("=====================================================================")
    
    broker = ApexProductionBroker()
    
    # 1. Place a passive BUY order deep below market price ($30,000) to ensure it sits as an open order
    print("⚡ Dispatching resting passive $30,000.00 LIMIT BUY order for BTCUSDT...")
    placement = await broker.submit_resting_limit_order(symbol="BTCUSDT", side="BUY", quantity=0.01, price=30000.0)
    
    order_id = placement.get("orderId")
    if order_id:
        print(f"🟢 [PLACEMENT ACK] Resting Order Registered | ID: {order_id} | Status: {placement.get('status')}")
        print("-" * 69)
        
        # Enforce a 2-second sleep window to let the engine populate the order book ledger
        await asyncio.sleep(2.0)
        
        # 2. Fire the active cancel sequence to clear the risk window
        cancel_receipt = await broker.cancel_active_order(symbol="BTCUSDT", order_id=order_id)
        
        if cancel_receipt:
            print("-" * 69)
            print("📋 CONFIRMED REMOVAL TRANSACTION RECEIPT:")
            print(f"  ├── Returned ID    : {cancel_receipt.get('orderId')}")
            print(f"  ├── Updated Status : {cancel_receipt.get('status')}")
            print(f"  └── Price Boundary : ${float(cancel_receipt.get('price', 0.0)):,.2f}")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(execute_lifecycle_sequence())
