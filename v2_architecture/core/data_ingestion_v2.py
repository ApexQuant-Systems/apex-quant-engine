import os
import sys
import pandas as pd
from pathlib import Path

class HistoricalDataIngestorV2:
    """
    Layer 1: Production Data Ingestion Engine v2.
    Loads real 1-minute historical datasets and executes strict mathematical 
    downsampling to build pristine multi-timeframe matrices.
    """
    def __init__(self, asset_symbol):
        self.symbol = asset_symbol
        self.raw_path = self._locate_csv_source()
        
    def _locate_csv_source(self):
        """Locates the existing archived raw data sheets within local storage vaults."""
        paths_to_check = [
            f"./data/raw/{self.symbol}/{self.symbol}_1m_archive.csv",
            f"./data/raw/{self.symbol}.csv",
            f"../data/raw/{self.symbol}_1m_archive.csv"
        ]
        for path in paths_to_check:
            if os.path.exists(path):
                return Path(path)
        raise FileNotFoundError(f"[🛑 INGESTION ERROR] No historical CSV source found for {self.symbol} inside local storage vaults.")

    def load_and_compile_matrix(self):
        """Loads 1m rows and applies vector resampling to build macro horizons."""
        print(f"[📡 INGESTION] Streaming source file: {self.raw_path} into memory...")
        
        # Load raw data rows efficiently
        df = pd.read_csv(self.raw_path)
        
        # Standardize primary tracking columns
        if 'timestamp' in df.columns and 'datetime' not in df.columns:
            # Handle both millisecond and second unix conversions dynamically
            unit = 'ms' if df['timestamp'].iloc[0] > 1e11 else 's'
            df['datetime'] = pd.to_datetime(df['timestamp'], unit=unit, utc=True)
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)
            
        df = df.sort_values('datetime').set_index('datetime')
        
        print("[📊 RESAMPLER] Compiling pristine macro timeframe arrays...")
        
        # Execute strict closed-interval downsampling definitions to block data leaks
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
        if 'volume' in df.columns:
            ohlc_rules['volume'] = 'sum'
            
        # Pinned lowercase strings to comply with strict modern pandas string specs
        df_15m = df.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_1h = df.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_4h = df.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_1d = df.resample('1d', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        # Restore raw numerical timestamp rows for matrix compatibility layers
        for frame in [df_15m, df_1h, df_4h, df_1d]:
            frame['timestamp'] = (frame['datetime'].astype('int64') // 10**6)
            
        print(f" [✓] Ingestion Matrix Complete | 15M: {len(df_15m)} | 1h: {len(df_1h)} | 4h: {len(df_4h)} | 1d: {len(df_1d)} bars.")
        return {
            '15m': df_15m,
            '1h': df_1h,
            '4h': df_4h,
            '1d': df_1d
        }

if __name__ == "__main__":
    try:
        ingestor = HistoricalDataIngestorV2("BTCUSDT")
        matrices = ingestor.load_and_compile_matrix()
        print("[✓] Layer 1 Data Ingestion v2 Module Verified.")
    except Exception as e:
        print(f"{e}\n[⚠️] Note: Place a valid historical CSV file inside your data/raw directory to run execution tests.")
