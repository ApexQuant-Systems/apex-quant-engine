import urllib.request
import os

assets = ["ETHUSDT", "SOLUSDT"]
# Target identical historical blocks to match your BTC structure (August 2025 as a baseline test)
url_templates = [
    "https://data.binance.vision/data/spot/monthly/klines/{amt}/1m/{amt}-1m-2025-08.zip"
]

print("[📥 DOWNLOADER] Fetching multi-asset validation fuel...")
for asset in assets:
    for template in url_templates:
        url = template.format(amt=asset)
        target_name = f"../{asset}-1m-2025-08.zip" # Place one folder back so the bootstrapper catches it
        
        if not os.path.exists(target_name):
            print(f"  -> Downloading archive for {asset}...")
            try:
                urllib.request.urlretrieve(url, target_name)
                print(f"  -> [✓] Saved {target_name}")
            except Exception as e:
                print(f"  -> [🛑] Failed to fetch {asset}: {e}")

