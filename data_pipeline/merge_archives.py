import os
import pandas as pd

def merge_all_horizons():
    processed_dir = "data/processed/"
    archive_dir = "data/archives/"
    os.makedirs(archive_dir, exist_ok=True)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("🛰️ APEX DATA PIPELINE: LAUNCHING STAGE 4 ARCHIVE CONSOLIDATION")
    print("=====================================================================")
    
    for symbol in symbols:
        symbol_processed_path = os.path.join(processed_dir, symbol)
        if not os.path.exists(symbol_processed_path):
            print(f"  ├── ⚠️ Skipping {symbol}: No processed files found found.")
            continue
            
        print(f"  ├── Aggregating historical chunks for: {symbol}")
        csv_files = sorted([f for f in os.listdir(symbol_processed_path) if f.endswith('.csv')])
        
        df_list = []
        for file_name in csv_files:
            file_path = os.path.join(symbol_processed_path, file_name)
            df_chunk = pd.read_csv(file_path)
            df_list.append(df_chunk)
            
        if not df_list:
            print(f"  ├── ⚠️ No processed chunks found for {symbol}.")
            continue
            
        # Combine the 2018-2023 blocks together
        df_deep = pd.concat(df_list, ignore_index=True)
        
        # Look for the existing 2024-2026 local vault files to stitch them together
        legacy_archive_variants = [
            f"data/raw/{symbol}/{symbol}-1m_archive.csv",
            f"data/raw/{symbol}/{symbol}_1m_archive.csv",
            f"data/raw/{symbol}-1m_archive.csv",
            f"data/raw/{symbol}_1m_archive.csv"
        ]
        
        legacy_df = None
        for variant in legacy_archive_variants:
            if os.path.exists(variant):
                print(f"  ├── 📂 Found existing 2024-2026 production vault: {variant}")
                try:
                    legacy_df = pd.read_csv(variant)
                    legacy_df.columns = [c.lower() for c in legacy_df.columns]
                    # Select only standard columns to match our processing schema
                    legacy_df = legacy_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    break
                except Exception as e:
                    print(f"  ├── ⚠️ Skipped reading production vault: {e}")
        
        if legacy_df is not None:
            df_deep = pd.concat([df_deep, legacy_df], ignore_index=True)
        
        # Clean up overlaps and sort chronologically
        initial_len = len(df_deep)
        df_deep.drop_duplicates(subset=['timestamp'], inplace=True)
        df_deep.sort_values(by=['timestamp'], inplace=True)
        final_len = len(df_deep)
        
        output_path = os.path.join(archive_dir, f"{symbol}_deep_8y_archive.csv")
        df_deep.to_csv(output_path, index=False)
        
        print(f"  └── 🎉 Success: Created {output_path}")
        print(f"      Rows stacked: {final_len:,} (Dropped {initial_len - final_len:,} duplicates)")
        
    print("=====================================================================")
    print("🏁 STAGE 4 COMPLETE: MACRO PORTFOLIO DATASETS ASSEMBLED IN data/archives/")

if __name__ == "__main__":
    merge_all_horizons()
