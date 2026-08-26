import os
import pandas as pd

def clean_and_reindex_vault():
    archive_dir = "data/archives/"
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("🛰️ APEX DATA PIPELINE: LAUNCHING STAGE 6 - BACKTEST COMPLIANCE BUILD")
    print("=====================================================================")
    
    for symbol in symbols:
        input_name = f"{symbol}_deep_8y_archive.csv"
        input_path = os.path.join(archive_dir, input_name)
        output_name = f"{symbol}_final_compliance.csv"
        output_path = os.path.join(archive_dir, output_name)
        
        if not os.path.exists(input_path):
            print(f"  ├── ❌ Error: Archive path not found for {input_name}")
            continue
            
        print(f"  🛠️ Aligning time-series sequences for: {symbol}")
        df = pd.read_csv(input_path)
        
        # Convert index over to standard datetime for chronological handling
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True) if pd.api.types.is_numeric_dtype(df['timestamp']) else pd.to_datetime(df['timestamp'], utc=True)
        df.set_index('datetime', inplace=True)
        
        # Construct a perfect, continuous 1-minute sequence grid
        perfect_grid = pd.date_range(start=df.index.min(), end=df.index.max(), freq='1min', tz='UTC')
        
        # Force reindexing to line up rows to the perfect chronological grid
        df_reindexed = df.reindex(perfect_grid)
        
        # Apply standard data filling rules to resolve the empty slots
        df_reindexed['close'] = df_reindexed['close'].ffill()
        df_reindexed['open'] = df_reindexed['open'].fillna(df_reindexed['close'])
        df_reindexed['high'] = df_reindexed['high'].fillna(df_reindexed['close'])
        df_reindexed['low'] = df_reindexed['low'].fillna(df_reindexed['close'])
        df_reindexed['volume'] = df_reindexed['volume'].fillna(0)
        
        # Rebuild native timestamp string column
        df_reindexed.reset_index(inplace=True)
        df_reindexed.rename(columns={'index': 'timestamp'}, inplace=True)
        
        # Isolate clean portfolio columns to ensure schema matching
        df_final = df_reindexed[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df_final.to_csv(output_path, index=False)
        
        print(f"      └── 🎉 Compliance Build Complete: {output_name}")
        print(f"          Original Rows: {len(df):,} ---> Reindexed Rows: {len(df_final):,}")
        
    print("=====================================================================")
    print("🏁 STAGE 6 COMPLETE: DEEP RECOVERY ARCHIVE PREPARED FOR SYSTEM TESTING")

if __name__ == "__main__":
    clean_and_reindex_vault()
