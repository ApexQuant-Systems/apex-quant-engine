import os
import pandas as pd

def audit_deep_vault():
    archive_dir = "data/archives/"
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("🛰️ APEX DATA PIPELINE: LAUNCHING STAGE 5 VAULT VALIDATION")
    print("=====================================================================")
    
    for symbol in symbols:
        file_name = f"{symbol}_deep_8y_archive.csv"
        file_path = os.path.join(archive_dir, file_name)
        
        if not os.path.exists(file_path):
            print(f"  ├── ❌ Error: Missing expected archive file {file_name}")
            continue
            
        print(f"  🔍 Auditing Time-Series Health For: {symbol}")
        try:
            # Low memory scanning for high-density files
            df = pd.read_csv(file_path)
            
            # 1. Inspect absolute boundaries
            total_rows = len(df)
            start_date = pd.to_datetime(df['timestamp'].iloc[0], unit='ms', utc=True) if str(df['timestamp'].iloc[0]).isdigit() else pd.to_datetime(df['timestamp'].iloc[0])
            end_date = pd.to_datetime(df['timestamp'].iloc[-1], unit='ms', utc=True) if str(df['timestamp'].iloc[-1]).isdigit() else pd.to_datetime(df['timestamp'].iloc[-1])
            
            # 2. Check for null or zero price anomalies
            zero_prices = df[(df['close'] <= 0) | (df['open'] <= 0)].shape[0]
            null_values = df.isnull().sum().sum()
            
            # 3. Time continuity test (Check for structural gaps)
            df['datetime_parsed'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True) if pd.api.types.is_numeric_dtype(df['timestamp']) else pd.to_datetime(df['timestamp'], utc=True)
            time_deltas = df['datetime_parsed'].diff().dropna()
            
            # Target any jumps greater than standard 1-minute interval (60 seconds)
            expected_delta = pd.Timedelta(minutes=1)
            gap_count = sum(time_deltas > expected_delta)
            
            print(f"      ├── Lifespan Range : {start_date.strftime('%Y-%m-%d')} ---> {end_date.strftime('%Y-%m-%d')}")
            print(f"      ├── Verified Rows  : {total_rows:,}")
            print(f"      ├── Null Elements  : {null_values}")
            print(f"      ├── Price Anomalies: {zero_prices}")
            print(f"      └── Detected Gaps  : {gap_count} timeline gaps")
            
            if gap_count == 0 and zero_prices == 0 and null_values == 0:
                print(f"      🏁 Verdict         : 🟢 PASSED INTEGRITY TESTS")
            else:
                print(f"      🏁 Verdict         : 🟡 DATA HEALTH WARNING (Gaps Present)")
                
        except Exception as e:
            print(f"  ├── 🔴 CRITICAL SYSTEM REJECTION DURING AUDIT: {e}")
            
    print("=====================================================================")
    print("🏁 STAGE 5 COMPLETE: COMPLIANCE INTEGRITY AUDITING RECORDED")

if __name__ == "__main__":
    audit_deep_vault()
