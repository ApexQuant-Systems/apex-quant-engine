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

class ApexStateBroker:
    """
    🛰️ APEX EXECUTION INFRASTRUCTURE: STAGE G LEVEL 4
    Implements institutional state query and atomic risk-mitigation vectors.
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
        except Exception as e:
            print(f"  ❌ [PLACEMENT ERROR] {e}")
            return {}

    async def fetch_order_status(self, symbol: str, order_id: int) -> dict:
        """Polls the exchange matching engine directly to verify specific order lifecycles."""
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
        req = urllib.request.Request(full_url, method="GET")
        req.add_header("X-MBX-APIKEY", self.api_key)
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"  ❌ [POLL ERROR] Failed to reconcile order status: {e}")
            return {}

    async def fetch_open_orders(self, symbol: str) -> list:
        """Aggregates the total open liability book currently running on the exchange asset."""
        endpoint = f"{self.base_url}/api/v3/openOrders"
        server_time = await self._get_server_time_ms()
        
        params = {
            "symbol": symbol.upper(),
            "timestamp": server_time,
            "recvWindow": 5000
        }
        query_string = urllib.parse.urlencode(params)
        signature = self._sign_payload(query_string)
        
        full_url = f"{endpoint}?{query_string}&signature={signature}"
        req = urllib.request.Request(full_url, method="GET")
        req.add_header("X-MBX-APIKEY", self.api_key)
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"  ❌ [OPEN ORDERS FETCH ERROR] Failed to poll order book: {e}")
            return []

    async def cancel_all_open_orders(self, symbol: str) -> list:
        """💥 ATOMIC PANIC SWITCH: Instantly flushes every single active open order on the symbol."""
        endpoint = f"{self.base_url}/api/v3/openOrders"
        server_time = await self._get_server_time_ms()
        
        params = {
            "symbol": symbol.upper(),
            "timestamp": server_time,
            "recvWindow": 5000
        }
        query_string = urllib.parse.urlencode(params)
        signature = self._sign_payload(query_string)
        
        full_url = f"{endpoint}?{query_string}&signature={signature}"
        req = urllib.request.Request(full_url, method="DELETE")
        req.add_header("X-MBX-APIKEY", self.api_key)
        
        print(f"🚨 [ATOMIC PANIC CALLED] Dispatched batch purge request for {symbol.upper()} open book...")
        start_time = time.perf_counter()
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            raw_response = json.loads(response.read().decode("utf-8"))
            latency = (time.perf_counter() - start_time) * 1000
            print(f"🚨 [PANIC ACK] All open orders purged. Purge execution RTT: {latency:.2f} ms")
            return raw_response
        except Exception as e:
            print(f"  ❌ [PANIC FAULT] Atomic book wipe was rejected by exchange engine: {e}")
            return []

async def execute_state_gauntlet():
    print("=====================================================================")
    print(" 🛰️  APEX BROKER SAFETY CORE: TESTING STAGE G.4 STATE MANAGEMENT")
    print("=====================================================================")
    
    broker = ApexStateBroker()
    symbol = "BTCUSDT"
    
    # 1. Place a passive resting order to create an open book state
    print("⚡ Step 1: Placing a resting $60,000.00 limit order...")
    placement = await broker.submit_resting_limit_order(symbol=symbol, side="BUY", quantity=0.01, price=60000.0)
    order_id = placement.get("orderId")
    
    if order_id:
        print(f"  └── Registered Order ID: {order_id}\n")
        await asyncio.sleep(1.0)
        
        # 2. Test explicit Order Polling
        print("⚡ Step 2: Testing isolated status polling via fetch_order_status()...")
        status_report = await broker.fetch_order_status(symbol=symbol, order_id=order_id)
        print(f"  └── Current Exchange State Confirmed: [{status_report.get('status')}]\n")
        await asyncio.sleep(1.0)
        
        # 3. Test open liability aggregation
        print("⚡ Step 3: Mapping aggregate book liabilities via fetch_open_orders()...")
        open_book = await broker.fetch_open_orders(symbol=symbol)
        print(f"  └── Active Open Orders Found in Book: {len(open_book)} Order(s)\n")
        await asyncio.sleep(1.0)
        
        # 4. Trigger the atomic purge panic switch
        print("⚡ Step 4: Activating atomic risk mitigation cancel-all switch...")
        purge_receipt = await broker.cancel_all_open_orders(symbol=symbol)
        print(f"  └── Total Canceled Entities Confirmed by Engine: {len(purge_receipt)}")
        
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(execute_state_gauntlet())
