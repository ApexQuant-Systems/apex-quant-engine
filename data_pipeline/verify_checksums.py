import os
import zipfile

def verify_raw_vault(start_year=2018, end_year=2023):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    raw_dir = "data/raw/"
    
    print("🛰️ APEX DATA PIPELINE: LAUNCHING STAGE 2 ARCHIVE VERIFICATION")
    print("=====================================================================")
    
    for symbol in symbols:
        print(f"\n🔍 Auditing Archive Integrity Ledger For: {symbol}")
        corrupt_count = 0
        valid_count = 0
        missing_or_skipped = 0
        
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                month_str = f"{month:02d}"
                file_name = f"{symbol}-1m-{year}-{month_str}.zip"
                file_path = os.path.join(raw_dir, file_name)
                
                if not os.path.exists(file_path):
                    missing_or_skipped += 1
                    continue
                    
                try:
                    # Perform low-level binary structure verification
                    if zipfile.is_zipfile(file_path):
                        with zipfile.ZipFile(file_path) as zf:
                            # Test zip archive integrity for CRC errors
                            test_result = zf.testzip()
                            if test_result is None:
                                valid_count += 1
                            else:
                                print(f"  ├── 🔴 CORRUPT CRC INTERNAL FILE: {file_name} -> {test_result}")
                                corrupt_count += 1
                    else:
                        print(f"  ├── 🔴 INVALID ZIP HEADER STRUCTURE: {file_name}")
                        corrupt_count += 1
                except Exception as e:
                    print(f"  ├── 🔴 DISK READ EXCEPTION: {file_name} ({e})")
                    corrupt_count += 1
                    
        print(f"  ├── Valid Sealed Archives  : {valid_count}")
        print(f"  ├── Skipped / Pre-listing  : {missing_or_skipped}")
        print(f"  └── Corrupted Data Blocks  : {corrupt_count}")
        
    print("\n=====================================================================")
    print("🏁 STAGE 2 COMPLETE: DATA FILE INTEGRITY LOGGED")

if __name__ == "__main__":
    verify_raw_vault()
