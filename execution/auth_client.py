import os
import asyncio
import time
import hmac
import hashlib
import urllib.request
import urllib.parse
import json

class AuthenticatedReadClient:
    """
    🛰️ APEX EXECUTION INFRASTRUCTURE: STAGE F PRIVATE CORE
    Handles cryptographic request signing and read-only account metadata retrieval.
    Features 0% trading/execution capability.
    """
    def __init__(self, env_path: str = ".env", base_url: str = "https://testnet.binance.vision"):
        self.base_url = base_url
        self.api_key = ""
        self.secret_key = ""
        self._load_credentials(env_path)

    def _load_credentials(self, env_path: str):
        """Extracts key pairs safely from local disk files without code strings."""
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

    def _generate_signature(self, query_string: str) -> str:
        """Signs the transaction data string natively using the HMAC-SHA256 protocol."""
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def _get_server_time_offset_ms(self) -> int:
        """Fetches exchange clock frame to completely insulate requests from local drift."""
        endpoint = f"{self.base_url}/api/v3/time"
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, urllib.request.urlopen, endpoint)
            raw = json.loads(response.read().decode("utf-8"))
            return raw.get("serverTime", int(time.time() * 1000))
        except Exception:
            return int(time.time() * 1000)

    async def fetch_account_balances(self):
        """Executes an authenticated read-only balance mapping operation."""
        if not self.api_key or not self.secret_key or "your_actual" in self.api_key:
            print("  ❌ [AUTH FAULT] API Key primitives missing or left as placeholder in your .env file.")
            return

        server_time = await self._get_server_time_offset_ms()
        params = {"timestamp": server_time, "recvWindow": 5000}
        query_string = urllib.parse.urlencode(params)
        signature = self._generate_signature(query_string)
        
        full_url = f"{self.base_url}/api/v3/account?{query_string}&signature={signature}"
        
        # Enforce secure signature authentication headers
        req = urllib.request.Request(full_url)
        req.add_header("X-MBX-APIKEY", self.api_key)
        
        print("⚡ Dispatched authenticated query to private server gateway...")
        start_time = time.perf_counter()
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            data = json.loads(response.read().decode("utf-8"))
            latency = (time.perf_counter() - start_time) * 1000
            
            print(f"🟢 [AUTH SUCCESS] Identity verified securely. RTT Latency: {latency:.2f} ms")
            print("-" * 69)
            print("💰 ACTIVE ACCOUNT ASSET BALANCES LOGGED:")
            
            # Filter down the payload to clean up console rows
            for asset in data.get("balances", []):
                free_balance = float(asset.get("free", 0.0))
                locked_balance = float(asset.get("locked", 0.0))
                if free_balance > 0.0 or locked_balance > 0.0:
                    print(f"  ├── Asset: {asset.get('asset'):<6} | Available: {free_balance:<12} | Locked: {locked_balance}")
                    
        except Exception as e:
            print(f"  ❌ [AUTHENTICATION REFUSED] Server handshake failed: {e}")

async def main():
    print("=====================================================================")
    print(" 🛰️  APEX EXECUTION: VERIFYING STAGE F AUTHENTICATED CHANNELS")
    print("=====================================================================")
    client = AuthenticatedReadClient()
    await client.fetch_account_balances()
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(main())
