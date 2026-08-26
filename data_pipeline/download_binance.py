import os
import sys
import requests
from urllib.parse import urljoin

def download_portfolio_archives(start_year=2018, end_year=2023):
    # Core asset universe mapped directly to your V3 configuration matrix
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    destination_dir = "data/raw/"
    os.makedirs(destination_dir, exist_ok=True)
    
    print("🛰️ APEX DATA PIPELINE: STARTING MULTI-ASSET INGESTION CAMPAIGN")
    print("=====================================================================")
    
    for symbol in symbols:
        print(f"\n🔄 Aggregating Historical Sheets For: {symbol}")
        base_url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/"
        
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                month_str = f"{month:02d}"
                file_name = f"{symbol}-1m-{year}-{month_str}.zip"
                target_url = urljoin(base_url, file_name)
                output_path = os.path.join(destination_dir, file_name)
                
                if os.path.exists(output_path):
                    print(f"  ├──  Already Cached: {file_name}")
                    continue
                    
                print(f"  ├──  Downloading: {file_name} ...", end="", flush=True)
                try:
                    response = requests.get(target_url, timeout=15)
                    if response.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        print(" [SUCCESS]")
                    elif response.status_code == 404:
                        print(" [NOT FOUND / SKIP]")
                    else:
                        print(f" [FAILED - STATUS {response.status_code}]")
                except Exception as e:
                    print(f" [ERROR: {e}]")
                    
    print("\n=====================================================================")
    print("🏁 STAGE 1 COMPLETE: PORTFOLIO ZIP ARCHIVES LOCALLY CACHED IN data/raw/")

if __name__ == "__main__":
    download_portfolio_archives()
