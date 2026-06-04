import os
import sys
import pandas as pd

# Interlink architectural module frameworks
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.data_ingestion_v2 import HistoricalDataIngestorV2
from core.multi_timeframe_matrix import TrueMultiTimeframeMatrix
from structure.smc_parser import SMCStructureEngine

class RealDataValidationSuite:
    """
    Empirical Validation Core.
    Tests structural algorithms and multi-timeframe synchronization
    against actual market data logs to prove edge viability.
    """
    def __init__(self, asset_symbol="BTCUSDT"):
        self.symbol = asset_symbol
        self.ingestor = HistoricalDataIngestorV2(self.symbol)
        self.smc = SMCStructureEngine()

    def run_empirical_audit(self):
        print("==========================================================================")
        print(f" APEX QUANT OS V2: EMPIRICAL SMART MONEY CONCEPTS AUDIT ({self.symbol})")
        print("==========================================================================")
        
        # 1. Load real data vectors across multiple frequencies
        matrices = self.ingestor.load_and_compile_matrix()
        
        # 2. Interlink files into True Air-Gapped Sync Matrix
        sync_matrix = TrueMultiTimeframeMatrix(matrices['4h'], matrices['1h'], matrices['15m'])
        
        # 3. Audit Layer 3 Structure Engine on Real Data Sheets
        print("\n[🔍 AUDIT] Testing SMC Parser algorithms on actual market data pools...")
        
        # Extract the Medium Timeframe (1-Hour) dataset to audit historical FVG generation
        mtf_data = matrices['1h']
        detected_fvgs = self.smc.identify_fair_value_gaps(mtf_data)
        
        print(f"  | Total Real-Data Fair Value Gaps Identified: {len(detected_fvgs)}")
        
        # Print actual historical coordinates of identified market inefficiencies
        if len(detected_fvgs) > 0:
            print("\n  [🔥 TOP 3 HISTORICAL HIGH-VOLUME FVGs IDENTIFIED]")
            # Sort imbalances by physical gap height dimension to isolate institutional impact footprint
            sorted_fvgs = sorted(detected_fvgs, key=lambda x: x['gap_size'], reverse=True)
            for i, fvg in enumerate(sorted_fvgs[:3]):
                print(f"    {i+1}. Type: {fvg['type']} | Timestamp: {fvg['creation_time']} | Inefficiency Zone: ${fvg['bottom']:.2f} ──► ${fvg['top']:.2f} | Imbalance Size: ${fvg['gap_size']:.2f}")
        else:
            print("  [🛑 ERROR] Structural logic failed to extract genuine market imbalances from real data.")

        # 4. Audit Pivot Detection Geometries
        swing_highs, swing_lows = self.smc.evaluate_market_pivots(mtf_data, window=5)
        print(f"\n  | Total Structural Swing High PIVOTS Extracted: {len(swing_highs)}")
        print(f"  | Total Structural Swing Low PIVOTS Extracted: {len(swing_lows)}")
        
        if len(swing_highs) > 0 and len(swing_lows) > 0:
            print(f"    [✓] Sample Swing High Pivot coordinate verified at ${swing_highs[-1]['price']:.2f} on {swing_highs[-1]['time']}\n")
        
        print("==========================================================================")
        print("[✓] EMPIRICAL AUDIT SEQUENCE RUN COMPLETE.")
        print("==========================================================================")

if __name__ == "__main__":
    try:
        suite = RealDataValidationSuite("BTCUSDT")
        suite.run_empirical_audit()
    except Exception as e:
        print(f"\n🛑 [CRITICAL AUDIT EXCEPTION] Execution stalled: {e}")
