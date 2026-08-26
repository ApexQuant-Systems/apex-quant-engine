import os
import zipfile
import pandas as pd
import glob

def prepare_data():
    raw_dir = "data/raw"
    output_file = "data/raw/BTCUSDT_2023.csv"
    
    # Get all 2023 zip files
    zip_files = sorted(glob.glob(f"{raw_dir}/BTCUSDT-1m-2023-*.zip"))
    
    if not zip_files:
        print("No zip files found!")
        return

    all_dfs = []
    for z_file in zip_files:
        print(f"Extracting {z_file}...")
        try:
            with zipfile.ZipFile(z_file, 'r') as z:
                csv_filename = z.namelist()[0]
                with z.open(csv_filename) as f:
                    # Binance monthly data typically has no headers
                    df = pd.read_csv(f, header=None)
                    df = df.iloc[:, 0:6]
                    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    all_dfs.append(df)
        except Exception as e:
            print(f"Failed on {z_file}: {e}")

    if all_dfs:
        print("Concatenating and saving...")
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.sort_values('timestamp', inplace=True)
        final_df.to_csv(output_file, index=False)
        print(f"Successfully saved {len(final_df)} rows to {output_file}")

if __name__ == "__main__":
    prepare_data()
