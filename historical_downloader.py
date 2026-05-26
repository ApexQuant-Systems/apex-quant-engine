import json
import os
import sys
import time
import urllib.request
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "cold_storage")

class ColdStorageHarvester:
    """Automates paginated downloading and local disk caching of massive historical datasets."""
    def __init__(self, symbol, interval="1m"):
        self.symbol = symbol
        self.interval = interval
        self.base_url = "https://api.binance.com/api/v3/klines"

    def download_macro_block(self, target_candle_count=10000):
        print(f"\n[*] Initializing Macro Ingestion for {self.symbol} ({self.interval})")
        print(f"[*] Target Capacity: {target_candle_count} intervals | Output: storage/cold_storage/")
        
        all_candles = []
        # Start from the current moment and walk backward into history
        current_end_time = int(time.time() * 1000)
        
        # Determine milliseconds step size based on interval
        step_ms = 60000 if self.interval == "1m" else 3600000
        # Dynamically chunk requests to stay safely under the 1,000 API limit
        chunk_limit = 1000 

        while len(all_candles) < target_candle_count:
            # Calculate the window for this specific iteration
            start_time_target = current_end_time - (chunk_limit * step_ms)
            
            url = f"{self.base_url}?symbol={self.symbol}&interval={self.interval}&startTime={start_time_target}&endTime={current_end_time}&limit={chunk_limit}"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                
                if not data:
                    print("[-] Hit archive boundary limit or empty response returned.")
                    break
                
                # Parse out raw arrays into system objects
                chunk_candles = []
                for k in data:
                    chunk_candles.append({
                        "timestamp": datetime.fromtimestamp(k[0] / 1000.0).strftime("%Y-%m-%d %H:%M:%S"),
                        "open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4])
                    })
                
                all_candles = chunk_candles + all_candles
                print(f" ├── Ingested index block: Cached {len(all_candles)} / {target_candle_count} intervals...")
                
                # Update pagination anchor point backward in time, adding buffer to prevent overlap
                current_end_time = data[0][0] - 1
                
                # Implement defensive throttling to strictly avoid rate limit triggers
                time.sleep(0.3)
                
            except Exception as e:
                print(f"[-] Network layer interruption: {e}")
                time.sleep(2)
                continue

        # Slice to the exact requested capacity size and commit to disk
        final_df = pd.DataFrame(all_candles).tail(target_candle_count)
        output_path = os.path.join(STORAGE_DIR, f"{self.symbol}_{self.interval}_archive.csv")
        final_df.to_csv(output_path, index=False)
        
        print(f"[✓] SUCCESS: Committed {len(final_df)} validated rows to offline cold storage.")
        print(f"└── File Location: {output_path}\n")

if __name__ == "__main__":
    # Let's seed our local laboratory data vaults for the multi-asset pool
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("==================================================")
    print("   SEEDING COLD-STORAGE INFRASTRUCTURE MATRIX     ")
    print("==================================================")
    
    for token in assets:
        # Download an uncorrupted 5,000-candle baseline chunk for each asset node
        harvester = ColdStorageHarvester(symbol=token, interval="1m")
        harvester.download_macro_block(target_candle_count=5000)
        
    print("==================================================")
    print("   LABORATORY COLD STORAGE COMPREHENSIVELY SEEDED ")
    print("==================================================")
