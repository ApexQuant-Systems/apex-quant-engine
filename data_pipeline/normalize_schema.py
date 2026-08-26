import os
import zipfile
import pandas as pd

def normalize_all_data():
    raw_dir = "data/raw/"
    processed_dir = "data/processed/"
    os.makedirs(processed_dir, exist_ok=True)
    
    print("🛰️ APEX DATA PIPELINE: LAUNCHING STAGE 3 SCHEMA NORMALIZATION")
    print("=====================================================================")
    
    # Standard institutional layout expected by the V3 core
    columns_layout = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    if not os.path.exists(raw_dir):
        print("  ❌ Critical: Raw data directory missing.")
        return
        
    files = sorted([f for f in os.listdir(raw_dir) if f.endswith('.zip')])
    
    for file_name in files:
        # Extract the parent token name (e.g., BTCUSDT)
        symbol = file_name.split('-')[0]
        symbol_dir = os.path.join(processed_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
        output_file = file_name.replace('.zip', '.csv')
        output_path = os.path.join(symbol_dir, output_file)
        
        if os.path.exists(output_path):
            print(f"  ├── Already Normalized: {symbol}/{output_file}")
            continue
            
        print(f"  ├── Processing: {file_name} ... ", end="", flush=True)
        try:
            zip_path = os.path.join(raw_dir, file_name)
            with zipfile.ZipFile(zip_path) as zf:
                # Target the raw internal text file
                csv_name = zf.namelist()[0]
                with zf.open(csv_name) as f:
                    # Binance monthly dumps are headerless CSV blocks
                    df = pd.read_csv(f, header=None)
                    
                    # Extract only the foundational OHLCV coordinates
                    df = df.iloc[:, :6]
                    df.columns = columns_layout
                    
                    # Commit clean standardized CSV block to partition disk
                    df.to_csv(output_path, index=False)
                    print("[SUCCESS]")
        except Exception as e:
            print(f"[FAILED: {e}]")
            
    print("=====================================================================")
    print("🏁 STAGE 3 COMPLETE: ALL PORTFOLIO SHEETS NORMALIZED IN data/processed/")

if __name__ == "__main__":
    normalize_all_data()
