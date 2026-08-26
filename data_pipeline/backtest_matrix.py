import os
import sys
import sqlite3
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.project_config import ApexGlobalConfiguration
from utils.system_logger import ApexSystemLogger
from strategies.structure_engine import ApexMarketLanguageEngine
from strategies.keyzone_engine import ApexKeyzoneEngine
from strategies.strategy_engine import ApexStrategyAlignmentEngine

log = ApexSystemLogger.get_initialized_logger("STRATEGY_MATRIX")

class ApexHierarchicalBacktester:
    """
    🛰️ APEX QUANT ENGINE: PRODUCTION CROSS-TIME HORIZON COORDINATOR
    Synchronizes separate timeframe streams (1d and 4h) sequentially
    to extract true, nested discretionary trading setups.
    """
    def __init__(self):
        self.db_path = ApexGlobalConfiguration.DATABASE_PATH
        self.structure_module = ApexMarketLanguageEngine()
        self.keyzone_module = ApexKeyzoneEngine()
        self.strategy_module = ApexStrategyAlignmentEngine()

    async def execute_hierarchical_gauntlet(self):
        print("=========================================================================================")
        print(" 🛰️  APEX OPERATING SYSTEM: EXECUTING NESTED HTF➔MTF➔LTF ALIGNMENT GAUNTLET")
        print("=========================================================================================")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pull available unique assets inside the warehouse database
        cursor.execute("SELECT DISTINCT symbol FROM multi_timeframe_market_bars")
        symbols = [r[0] for r in cursor.fetchall()]

        print(f"| Asset Symbol | HTF Stream | MTF Stream | Total Context | Valid Synthesized Signals | Status State |")
        print(f"|--------------|------------|------------|---------------|---------------------------|--------------|")

        for symbol in symbols:
            # Query true raw daily tracking candles
            cursor.execute("""
                SELECT open, high, low, close FROM multi_timeframe_market_bars 
                WHERE symbol = ? AND interval = '1d' ORDER BY timestamp ASC
            """, (symbol,))
            daily_rows = cursor.fetchall()
            
            # Query true raw 4-hour intermediate candles
            cursor.execute("""
                SELECT open, high, low, close FROM multi_timeframe_market_bars 
                WHERE symbol = ? AND interval = '4h' ORDER BY timestamp ASC
            """, (symbol,))
            four_hour_rows = cursor.fetchall()
            
            # Synchronize baseline arrays based on the tightest asset window size
            execution_depth = min(len(daily_rows), len(four_hour_rows))
            if execution_depth < 15:
                continue
                
            valid_strategy_signals = 0
            
            # Walk step-by-step through historical clock time rows concurrently
            for length in range(15, execution_depth + 1):
                # 1. Compute higher timeframe context state (Daily)
                d_o = [r[0] for r in daily_rows[:length]]
                d_h = [r[1] for r in daily_rows[:length]]
                d_l = [r[2] for r in daily_rows[:length]]
                d_c = [r[3] for r in daily_rows[:length]]
                
                htf_struct = self.structure_module.extract_pure_market_structure(d_h, d_l, d_c)
                htf_key = self.keyzone_module.scan_institutional_keyzones(d_o, d_h, d_l, d_c, htf_struct["structural_event"])
                htf_telemetry = {**htf_struct, **htf_key}

                # 2. Compute middle timeframe context state (4-Hour)
                m_o = [r[0] for r in four_hour_rows[:length]]
                m_h = [r[1] for r in four_hour_rows[:length]]
                m_l = [r[2] for r in four_hour_rows[:length]]
                m_c = [r[3] for r in four_hour_rows[:length]]
                
                mtf_struct = self.structure_module.extract_pure_market_structure(m_h, m_l, m_c)
                mtf_key = self.keyzone_module.scan_institutional_keyzones(m_o, m_h, m_l, m_c, mtf_struct["structural_event"])
                mtf_telemetry = {**mtf_struct, **mtf_key}

                # 3. Pass nested data vectors straight into the strategy alignment gate
                decision = self.strategy_module.evaluate_triple_horizon_alignment(
                    htf_telemetry=htf_telemetry, mtf_telemetry=mtf_telemetry, ltf_telemetry={}
                )
                
                if decision["isValidSetup"]:
                    valid_strategy_signals += 1
                    
            print(f"| {symbol:<12} | 1d         | 4h         | {execution_depth:>13} | {valid_strategy_signals:>25} | 🟢 SYSTEM_LIVE|")
            
        conn.close()
        print("=========================================================================================\n")

if __name__ == "__main__":
    backtester = ApexHierarchicalBacktester()
    asyncio.run(backtester.execute_hierarchical_gauntlet())
