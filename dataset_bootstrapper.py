import os
import csv
import zipfile
import glob
from pathlib import Path
from typing import Generator, Dict, Any, List

class LocalDataFeedEngine:
    def __init__(self, root_dir: str = "."):
        self.root_path = Path(root_dir)
        self.raw_vault = self.root_path / "data" / "raw"
        self.processed_vault = self.root_path / "data" / "processed"
        
    def build_vault_structure(self) -> None:
        """Phase 1: Establishes institutional data paths."""
        print("[📁 VAULT] Enforcing data warehouse folder structure...")
        self.raw_vault.mkdir(parents=True, exist_ok=True)
        self.processed_vault.mkdir(parents=True, exist_ok=True)
        
    def bootstrap_datasets(self) -> None:
        """Phase 3: Automatically detects, extracts, and routes home directory datasets."""
        print("[⚡ BOOTSTRAP] Scanning workspace and home directory for raw historical assets...")
        
        # Look in current folder and one folder backward (home directory where your loose files are)
        target_patterns = ["*.csv", "*.zip", "../*.csv", "../*.zip"]
        discovered_files = []
        for pattern in target_patterns:
            discovered_files.extend(glob.glob(str(self.root_path / pattern)))
            
        for file_path in set(discovered_files):
            path = Path(file_path)
            if "dataset_bootstrapper.py" in path.name or "historical_replay_harness.py" in path.name:
                continue
                
            # Extract asset ticker tokens (e.g., BTCUSDT)
            ticker = path.name.split('-')[0].upper()
            ticker_dir = self.raw_vault / ticker
            ticker_dir.mkdir(parents=True, exist_ok=True)
            
            # Auto-unzip directly into the organized vault
            if path.suffix.lower() == ".zip":
                print(f"  -> Decompressing archive asset: {path.name} -> {ticker_dir}")
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(ticker_dir)
            
            # Relocate raw loose CSV files to the clean sub-directory
            elif path.suffix.lower() == ".csv":
                destination = ticker_dir / path.name
                if not destination.exists():
                    print(f"  -> Relocating loose data asset: {path.name} -> {ticker_dir}")
                    import shutil
                    shutil.copy2(path, destination)

    def stream_chronological_feed(self, ticker: str, schema: Dict[str, int]) -> Generator[Dict[str, Any], None, None]:
        """Phase 2: Ultra-low-latency user-space localized data feed engine."""
        ticker_dir = self.raw_vault / ticker.upper()
        csv_files = sorted(glob.glob(str(ticker_dir / "*.csv")))
        
        if not csv_files:
            print(f"[🛑 ERROR] No data variants loaded for asset profile: {ticker}")
            return
            
        print(f"[🚀 ENGINE] Commencing zero-latency streaming matrix for [{ticker}] across {len(csv_files)} partitions...")
        
        for csv_file in csv_files:
            with open(csv_file, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
                if first_row and not first_row[0].isdigit():
                    pass 
                elif first_row:
                    yield self._parse_row(first_row, ticker, schema)
                    
                for row in reader:
                    if row:
                        yield self._parse_row(row, ticker, schema)

    def _parse_row(self, row: List[str], ticker: str, schema: Dict[str, int]) -> Dict[str, Any]:
        return {
            "ticker": ticker,
            "timestamp": int(float(row[schema["timestamp"]])),
            "open": float(row[schema["open"]]),
            "high": float(row[schema["high"]]),
            "low": float(row[schema["low"]]),
            "close": float(row[schema["close"]]),
            "volume": float(row[schema["volume"]])
        }

if __name__ == "__main__":
    csv_config = {"timestamp": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5}
    
    engine = LocalDataFeedEngine()
    engine.build_vault_structure()
    engine.bootstrap_datasets()
    
    feed = engine.stream_chronological_feed("BTCUSDT", schema=csv_config)
    print("\n[🔬 STREAM AUDIT] Sampling localized memory output matrix:")
    for _ in range(3):
        try:
            print(next(feed))
        except StopIteration:
            print("  -> Vault tracking verification completed.")
            break
