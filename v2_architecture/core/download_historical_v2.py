import os
import sys
import pandas as pd
from pathlib import Path

# Ensure ccxt is accessible in the local execution context
try:
    import ccxt
except ImportError:
    print("[🛑 ERROR] ccxt package missing. Run: pip install ccxt")
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def inject_real_market_fuel(symbol_pair="BTC/USDT", target_filename="BTCUSDT.csv"):
    print("==========================================================================")
    print(f"[📡 FUEL INJECTOR] Initializing REST Gateway to fetch real market history")
    print("==========================================================================")
    
    # Initialize public exchange connector
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'} # Targets highly liquid futures market order books
    })
    
    try:
        print(f"[*] Downloading deepest available 1-minute closed bars for {symbol_pair}...")
        # Fetch 1,000 pristine real-world 1m historical data blocks
        ohlcv = exchange.fetch_ohlcv(symbol_pair, timeframe='1m', limit=1000)
        
        # Structure directly into the exact canonical matrix format required by Layer 1
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Enforce destination directory creation matching validation suite configurations
        destination_dir = Path("./data/raw")
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        output_filepath = destination_dir / target_filename
        df.to_csv(output_filepath, index=False)
        
        print(f"\n[✓] SUCCESS: Loaded {len(df)} authentic historical market candles.")
        print(f"💾 File pinned securely at target destination path: {output_filepath}")
        print("==========================================================================")
        
    except Exception as e:
        print(f"\n🛑 [NETWORK EXCEPTION] Gateway connection failed or was throttled: {e}")
        print("==========================================================================")

if __name__ == "__main__":
    inject_real_market_fuel()
