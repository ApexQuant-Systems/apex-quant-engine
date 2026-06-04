import os
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.data_ingestion_v2 import HistoricalDataIngestorV2
from core.multi_timeframe_matrix import TrueMultiTimeframeMatrix
from core.risk_engine_v2 import InstitutionalRiskEngine
from core.regime_classifier import MarketRegimeClassifier
from structure.smc_parser import SMCStructureEngine

class AlphaDiscoveryEngineV2:
    """
    Phase 4 Empirical Discovery Core.
    Validates synchronized long/short SMC modules across dynamic macro regimes.
    """
    def __init__(self, symbol="BTCUSDT", initial_balance=10000.0, target_rr=4.0):
        self.symbol = symbol
        self.balance = initial_balance
        self.equity_curve = [initial_balance]
        self.target_rr = target_rr
        
        self.ingestor = HistoricalDataIngestorV2(self.symbol)
        self.smc = SMCStructureEngine()
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def run_simulation(self):
        print("==========================================================================")
        print(f" INITIALIZING DUAL-SIDED ALPHA MATRIX SYSTEM: {self.symbol}")
        print("==========================================================================")
        
        matrices = self.ingestor.load_and_compile_matrix()
        sync_matrix = TrueMultiTimeframeMatrix(matrices['4h'], matrices['1h'], matrices['15m'])
        
        ltf_records = sync_matrix.ltf.to_dict('records')
        active_position = None
        journal = []
        
        print(f"\n[*] Commencing chronological backtest loop over {len(ltf_records):,} ticks...")
        
        for idx in range(100, len(ltf_records)):
            tick = ltf_records[idx]
            current_time = tick['datetime']
            current_price = tick['close']
            
            # --- 1. POSITION LIQUIDATION ENVELOPE MANAGEMENT ---
            if active_position:
                pos = active_position
                if pos['direction'] == 'LONG':
                    if tick['low'] <= pos['sl']:
                        self.balance -= pos['risk_capital']
                        journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital'], 'regime': pos['regime'], 'side': 'LONG'})
                        active_position = None
                        continue
                    elif tick['high'] >= pos['tp']:
                        self.balance += pos['risk_capital'] * self.target_rr
                        journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr, 'regime': pos['regime'], 'side': 'LONG'})
                        active_position = None
                        continue
                elif pos['direction'] == 'SHORT':
                    if tick['high'] >= pos['sl']:
                        self.balance -= pos['risk_capital']
                        journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital'], 'regime': pos['regime'], 'side': 'SHORT'})
                        active_position = None
                        continue
                    elif tick['low'] <= pos['tp']:
                        self.balance += pos['risk_capital'] * self.target_rr
                        journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr, 'regime': pos['regime'], 'side': 'SHORT'})
                        active_position = None
                        continue
            
            # --- 2. MULTI-TIMEFRAME CONFLUENCE OVERLAYS ---
            visible_state = sync_matrix.get_visible_state(current_time)
            htf_frame = visible_state['closed_htf']
            mtf_frame = visible_state['closed_mtf']
            
            if len(htf_frame) < 50 or len(mtf_frame) < 50:
                continue
                
            # Gate A: Intercept Dynamic Higher-Timeframe Regime
            regime = MarketRegimeClassifier.classify_regime(htf_frame)
            if regime == "CHOPPY_RANGE":
                continue # Hard stop: Insulate assets from toxic ranges
                
            # Gate B: Premium vs Discount Array Mapping
            htf_high = htf_frame['high'].tail(30).max()
            htf_low = htf_frame['low'].tail(30).min()
            equilibrium = (htf_high + htf_low) / 2.0
            
            # Gate C: MTF Structural Inefficiency Parsing
            mtf_fvgs = self.smc.identify_fair_value_gaps(mtf_frame)
            
            # Gate D: LTF Displacement Pivot Breaks (CHOCH)
            recent_ltf_window = sync_matrix.ltf.iloc[idx-8:idx]
            ltf_highs, ltf_lows = self.smc.evaluate_market_pivots(recent_ltf_window, window=2)
            
            # --- 3. DUAL-ENGINE TRANS-ACTIVATION LOGIC GATES ---
            if not active_position:
                # ====== LONG CORE EXECUTION BLOCK ======
                if regime == "TRENDING_BULL":
                    is_in_discount = current_price < equilibrium
                    unmitigated_bull_fvg = any(fvg['type'] == 'BULLISH' and fvg['top'] > current_price for fvg in mtf_fvgs[-5:])
                    is_ltf_bull_choch = len(ltf_highs) > 0 and current_price > ltf_highs[-1]['price']
                    
                    if is_in_discount and unmitigated_bull_fvg and is_ltf_bull_choch:
                        sl_price = tick['low'] * 0.995
                        size = self.risk_engine.calculate_position_size(self.balance, current_price, sl_price, self.instrument_config)
                        
                        if size > 0:
                            active_position = {
                                'direction': 'LONG', 'sl': sl_price, 'risk_capital': size * abs(current_price - sl_price),
                                'tp': current_price + (abs(current_price - sl_price) * self.target_rr), 'regime': regime
                            }
                
                # ====== SHORT CORE EXECUTION BLOCK ======
                elif regime == "TRENDING_BEAR":
                    is_in_premium = current_price > equilibrium
                    unmitigated_bear_fvg = any(fvg['type'] == 'BEARISH' and fvg['bottom'] < current_price for fvg in mtf_fvgs[-5:])
                    is_ltf_bear_choch = len(ltf_lows) > 0 and current_price < ltf_lows[-1]['price']
                    
                    if is_in_premium and unmitigated_bear_fvg and is_ltf_bear_choch:
                        sl_price = tick['high'] * 1.005
                        size = self.risk_engine.calculate_position_size(self.balance, current_price, sl_price, self.instrument_config)
                        
                        if size > 0:
                            active_position = {
                                'direction': 'SHORT', 'sl': sl_price, 'risk_capital': size * abs(sl_price - current_price),
                                'tp': current_price - (abs(sl_price - current_price) * self.target_rr), 'regime': regime
                            }

        # --- 4. PRINT GLOBAL DISCOVERY REPORT ---
        print("\n==========================================================================")
        print(" ALPHA READOUT COMPILATION REPORT SECURED")
        print("==========================================================================")
        
        if len(journal) == 0:
            print("[⚠️ RETRACTION] No trade opportunities matched the high-conviction logic.")
            return
            
        df_journal = pd.DataFrame(journal)
        total_trades = len(df_journal)
        wins = len(df_journal[df_journal['status'] == 'WIN'])
        win_rate = (wins / total_trades) * 100
        
        total_won = df_journal[df_journal['pnl'] > 0]['pnl'].sum()
        total_lost = abs(df_journal[df_journal['pnl'] < 0]['pnl'].sum())
        profit_factor = total_won / total_lost if total_lost > 0 else total_won
        
        print(f"  🏁 Total Trades Handled: {total_trades}")
        print(f"  🎯 Net Win Rate Factor:  {win_rate:.2f}%")
        print(f"  📊 Global Profit Factor: {profit_factor:.2f}")
        print(f"  💰 Ending Balance Yield: $ {self.balance:,.2f}")
        
        print("\n  [🔬 SECTOR ABLATION SPLIT PERFORMANCE LOGS]")
        for side in ['LONG', 'SHORT']:
            sub = df_journal[df_journal['side'] == side]
            if not sub.empty:
                s_wins = len(sub[sub['status'] == 'WIN'])
                print(f"    │ -> Side [{side:5s}] | Executions: {len(sub):3d} | Win Rate: {(s_wins/len(sub))*100:5.2f}% | Net PnL: ${sub['pnl'].sum():+,.2f}")
        print("==========================================================================")

if __name__ == "__main__":
    discovery = AlphaDiscoveryEngineV2()
    discovery.run_simulation()
