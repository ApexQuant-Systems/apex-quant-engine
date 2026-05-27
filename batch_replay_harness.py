import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from historical_replay_engine import DynamicReplayChamber
from strategies.profile_manifest import IntradaySniperProfile, SwingVanguardProfile

class MacroStatisticalHarness:
    """Automates multi-asset, multi-profile simulation routines to harvest raw expectancy metrics."""
    def __init__(self, assets, lookback_candles=1000):
        self.assets = assets
        self.lookback = lookback_candles
        self.profiles = [IntradaySniperProfile(), SwingVanguardProfile()]

    def execute_global_harvest(self):
        print("\n==================================================================")
        print(f"   APEX QUANT SYSTEMS: BATCH REPLAY HARNESS MASTER RUN ({self.lookback} Bars)")
        print("==================================================================")
        
        for profile in self.profiles:
            print(f"\n[🚀] ENGAGING PROFILE CARTRIDGE: [{profile.name}] (Timeframe: {profile.timeframe})")
            print("──────────────────────────────────────────────────────────────────")
            
            # Spin up an isolated simulation chamber for the active profile
            chamber = DynamicReplayChamber(profile)
            
            for asset in self.assets:
                print(f"\n[*] Launching warp sequence -> Asset: {asset} | Lookback: {self.lookback} bars")
                start_time = datetime.now()
                
                # Execute the dynamic simulation over the deep data array
                chamber.run_time_warp(asset, lookback_minutes=self.lookback)
                
                duration = (datetime.now() - start_time).total_seconds()
                print(f"[✓] Completed {asset} simulation in {duration:.2f} seconds.")
                
        self._print_operator_verdict()

    def _print_operator_verdict(self):
        print("\n==================================================================")
        print("   GLOBAL HARVEST COMPLETE — METRIC EXTRACTION READY            ")
        print("==================================================================")
        print(" [▶] NEXT OPERATOR ACTION:")
        print(" 1. Run 'python3 analytics_dashboard.py' to evaluate realized edge yields.")
        print(" 2. Run 'python3 denial_analyzer.py' to compute total filter efficiency.")
        print("==================================================================\n")

if __name__ == "__main__":
    target_crypto_matrix = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    # Initialize the macro harness to extract truth over a deep 1,000-candle matrix window
    harvest_controller = MacroStatisticalHarness(target_crypto_matrix, lookback_candles= None)
    harvest_controller.execute_global_harvest()

