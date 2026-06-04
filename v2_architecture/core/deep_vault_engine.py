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

class DeepVaultDownloaderV2:
    """
    Layer 1: Historical Deep Vault Engine (Multi-Year Upgrade).
    Scrolls chronologically from a fixed multi-year historical epoch anchor.
    """
    def __init__(self, exchange_id='binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
    def download_multi_year_history(self, symbol="BTC/USDT"):
        clean_symbol = symbol.replace('/', '').replace(':', '')
        print("==========================================================================")
        print(f" INITIALIZING MULTI-YEAR HISTORICAL EXCAVATION: {symbol}")
        print("==========================================================================")
        
        # Fixed epoch anchor: January 1, 2024
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        since_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        all_candles = []
        pagination_count = 0
        
        print(f"[*] Launching chronological loop from: {start_date.strftime('%Y-%m-%d')}")
        
        while since_timestamp < end_timestamp:
            try:
                candles = self.exchange.fetch_ohlcv(symbol, timeframe='1m', since=since_timestamp, limit=1000)
                if not candles:
                    print("\n[✓] Historical timeline edge reached.")
                    break
                    
                pagination_count += 1
                all_candles.extend(candles)
                
                # Step cursor forward by 1 minute past the final candle in the block
                since_timestamp = candles[-1][0] + 60000
                
                current_cursor_date = datetime.fromtimestamp(candles[-1][0] / 1000, tz=timezone.utc)
                print(f"  | Block #{pagination_count:04d} | Total Rows: {len(all_candles):,} | Position: {current_cursor_date.strftime('%Y-%m-%d %H:%M')}", end="\r")
                
                time.sleep(self.exchange.rateLimit / 1000 if self.exchange.rateLimit else 0.4)
                
            except Exception as e:
                print(f"\n[⚠️ NET DELAY] Cool-down intercept triggered: {e}")
                time.sleep(4)
                
        if len(all_candles) == 0:
            print("[🛑 ERROR] Zero rows retrieved.")
            return False
            
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        output_dir = Path(f"./data/raw/{clean_symbol}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{clean_symbol}_1m_archive.csv"
        df.to_csv(output_file, index=False)
        
        print("\n--------------------------------------------------------------------------")
        print(f"[✓] COMPILATION COMPLETE: Multi-Year Archive Secured.")
        print(f"  | Total Ingested Intervals: {len(df):,} rows.")
        print(f"  | File Location: {output_file}")
        print("==========================================================================")
        return True

if __name__ == "__main__":
    downloader = DeepVaultDownloaderV2()
    downloader.download_multi_year_history("BTC/USDT")
