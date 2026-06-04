import os
import sys
import pandas as pd
import numpy as np

# Bind architectural paths across core folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.multi_timeframe_matrix import TrueMultiTimeframeMatrix
from core.risk_engine_v2 import InstitutionalRiskEngine
from strategies.orchestrator_v2 import HighConvictionOrchestrator

class ApexV2SystemsHarness:
    """
    Master Integration Chassis for Apex Quant OS v2.
    Interlinks Timeframe Matrix, SMC Parser, Strategy Filters, and Risk Clamps.
    """
    def __init__(self, target_asset="BTC/USDT"):
        self.asset = target_asset
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_synchronized_mock_market(self, bar_count=300):
        """
        Builds three independent data streams with true time-frequency intervals
        to check structural data flow performance.
        """
        print("[📊 DATA MATRIX] Generating independent multi-timeframe time-series data...")
        end_time = pd.Timestamp("2026-06-03 12:00:00", tz="UTC")
        
        # 1. Low Timeframe Base Grid (15-Minute Bars)
        ltf_times = pd.date_range(end=end_time, periods=bar_count, freq="15min")
        ltf_df = pd.DataFrame({
            'timestamp': [int(t.timestamp() * 1000) for t in ltf_times],
            'open': np.random.uniform(67000, 67500, bar_count),
            'high': np.random.uniform(67500, 68000, bar_count),
            'low': np.random.uniform(66500, 67000, bar_count),
            'close': np.random.uniform(67000, 67500, bar_count)
        })
        
        # 2. Medium Timeframe Base Grid (1-Hour Bars)
        mtf_times = pd.date_range(end=end_time, periods=bar_count, freq="1h")
        mtf_df = pd.DataFrame({
            'timestamp': [int(t.timestamp() * 1000) for t in mtf_times],
            'open': np.random.uniform(66800, 67400, bar_count),
            'high': np.random.uniform(67400, 68200, bar_count),
            'low': np.random.uniform(66200, 66800, bar_count),
            'close': np.random.uniform(66800, 67400, bar_count)
        })
        
        # 3. High Timeframe Base Grid (4-Hour Bars)
        htf_times = pd.date_range(end=end_time, periods=bar_count, freq="4h")
        htf_df = pd.DataFrame({
            'timestamp': [int(t.timestamp() * 1000) for t in htf_times],
            'open': np.random.uniform(66000, 67000, bar_count),
            'high': np.random.uniform(67000, 68500, bar_count),
            'low': np.random.uniform(65500, 66000, bar_count),
            'close': np.random.uniform(66000, 67000, bar_count)
        })
        
        return htf_df, mtf_df, ltf_df

    def execute_system_run(self):
        print("==========================================================================")
        print(" INITIALIZING APEX QUANT OS V2: END-TO-END INTEGRATION HARNESS")
        print("==========================================================================")
        
        # Load independent dataframes into processing scopes
        htf, mtf, ltf = self.generate_synchronized_mock_market()
        
        # Initialize true air-gapped timeframe sync engine
        sync_matrix = TrueMultiTimeframeMatrix(htf, mtf, ltf)
        
        # Instantiate Strategy Orchestrator Core linking SMC rules
        orchestrator = HighConvictionOrchestrator(sync_matrix, target_rr=4.0)
        
        # Run chronological loop execution check
        print("\n[🎬 RUNNER] Booting chronological time execution loop...")
        orchestrator.evaluate_tick_stream()
        
        # Verify an arbitrary execution sizing sequence to confirm system link viability
        print("\n[🎯 RISK INTEGRATION] Validating Risk Engine loop connection via mock execution state...")
        account_balance = 50000.0  # $50k funding challenge target profile
        entry_sample = 67200.0
        sl_sample = 66800.0
        
        allocated_lots = self.risk_engine.calculate_position_size(
            account_balance, entry_sample, sl_sample, self.instrument_config
        )
        print(f" [✓] Verification Complete: $ {account_balance} balance at ${entry_sample} Entry returns allocation payload: {allocated_lots} units.")
        print("==========================================================================")

if __name__ == "__main__":
    harness = ApexV2SystemsHarness()
    harness.execute_system_run()
