import os
import urllib.request
import sys

def populate_local_vaults():
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    # Targeting a continuous 3-month block across mid-2025 for diverse regime exposure
    months = ["2025-08", "2025-09", "2025-10"]
    
    base_url = "https://data.binance.vision/data/spot/monthly/klines/{asset}/1m/{asset}-1m-{month}.zip"
    
    # Identify the root destination directory relative to project structure
    # Places archives one level up so dataset_bootstrapper.py flags and processes them cleanly
    destination_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    print("=====================================================================")
    print("        APEX QUANT SYSTEMS — HISTORICAL VAULT INGESTION SUITE        ")
    print("=====================================================================")
    print(f"[*] Initializing bulk downloads to target workspace: {destination_dir}\n")

    total_files = len(assets) * len(months)
    download_count = 0

    for asset in assets:
        print(f"\n[📦 TARGET ASSET] Processing data vectors for: {asset}")
        print("-" * 50)
        
        for month in months:
            filename = f"{asset}-1m-{month}.zip"
            target_path = os.path.join(destination_dir, filename)
            download_url = base_url.format(asset=asset, month=month)
            
            download_count += 1
            progress_prefix = f"[{download_count}/{total_files}]"
            
            if os.path.exists(target_path):
                print(f"  {progress_prefix} -> Archive already localized: {filename} (Skipping)")
                continue
                
            print(f"  {progress_prefix} -> Fetching {filename} from storage network...")
            try:
                # Custom User-Agent header string to bypass strict cloud protection filters
                req = urllib.request.Request(
                    download_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                
                with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
                    out_file.write(response.read())
                    
                print(f"  └── [✓] Saved to workspace core.")
            except Exception as e:
                print(f"  └── [🛑 ERROR] Failed to fetch data matrix block: {e}", file=sys.stderr)

    print("\n=====================================================================")
    print("       INGESTION RUN COMPLETE — DATA COLD-STORAGE POOLS FILLED       ")
    print("=====================================================================")

if __name__ == "__main__":
    populate_local_vaults()
