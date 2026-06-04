import os
import sys
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

try:
    import ccxt
except ImportError:
    print("[🛑 ERROR] ccxt missing. Run: pip install ccxt")
    sys.exit(1)

def download_asset_vault(symbol):
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    clean_symbol = symbol.replace('/', '').replace(':', '')
    
    print(f"\n[*] Launching Excavation for: {symbol}")
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    since_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    all_candles = []
    pagination = 0
    
    while since_timestamp < end_timestamp:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe='1m', since=since_timestamp, limit=1000)
            if not candles:
                break
            pagination += 1
            all_candles.extend(candles)
            since_timestamp = candles[-1][0] + 60000
            
            current_date = datetime.fromtimestamp(candles[-1][0] / 1000, tz=timezone.utc)
            print(f"  | Block #{pagination:04d} | Total Rows: {len(all_candles):,} | Cursor: {current_date.strftime('%Y-%m-%d')}", end="\r")
            time.sleep(exchange.rateLimit / 1000 if exchange.rateLimit else 0.4)
        except Exception as e:
            time.sleep(5)
            
    if len(all_candles) == 0:
        return False
        
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    output_dir = Path(f"./data/raw/{clean_symbol}")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / f"{clean_symbol}_1m_archive.csv", index=False)
    print(f"\n[✓] Secure Vault Locked for {clean_symbol}: {len(df):,} rows.")
    return True

if __name__ == "__main__":
    print("==========================================================================")
    print(" APEX QUANT OS V2: BATCH HISTORICAL INGESTION PIPELINE")
    print("==========================================================================")
    for asset in ["ETH/USDT", "SOL/USDT"]:
        download_asset_vault(asset)
    print("==========================================================================")
