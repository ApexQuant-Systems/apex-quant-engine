import os
import sys
import pandas as pd
import numpy as np

# Bind core systematic layout frameworks
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.data_ingestion_v2 import HistoricalDataIngestorV2
from core.multi_timeframe_matrix import TrueMultiTimeframeMatrix
from core.risk_engine_v2 import InstitutionalRiskEngine
from core.regime_classifier import MarketRegimeClassifier
from structure.smc_parser import SMCStructureEngine

class StrategyTournamentEngine:
    """
    Layer 4: Advanced R&D Alpha Discovery Factory.
    Simulates separate algorithmic rule variations across real market 
    data to locate repeatable mathematical edges.
    """
    def __init__(self, symbol="BTCUSDT", initial_balance=10000.0, target_rr=4.0):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.target_rr = target_rr
        
        self.ingestor = HistoricalDataIngestorV2(self.symbol)
        self.smc = SMCStructureEngine()
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def execute_tournament(self):
        print("==========================================================================")
        print(f" INITIALIZING PHASE 4 ALPHA DISCOVERY: TOURNAMENT MATRIX RUN ({self.symbol})")
        print("==========================================================================")
        
        # Ingest deep real history arrays once to keep hardware execution speeds high
        matrices = self.ingestor.load_and_compile_matrix()
        sync_matrix = TrueMultiTimeframeMatrix(matrices['4h'], matrices['1h'], matrices['15m'])
        ltf_records = sync_matrix.ltf.to_dict('records')
        
        # Define structural variant profiles
        variants = ['APEX_ULTRA', 'CORE_SHIFT', 'MOM_FLOW', 'SWEEP_ONLY']
        leaderboard = {}
        
        for variant in variants:
            print(f"[*] Simulating variant pipeline track: [{variant}]...")
            balance = self.initial_balance
            active_position = None
            journal = []
            
            for idx in range(100, len(ltf_records)):
                tick = ltf_records[idx]
                current_time = tick['datetime']
                current_price = tick['close']
                
                # --- POSITION EXECUTION LAYER ---
                if active_position:
                    pos = active_position
                    if pos['direction'] == 'LONG':
                        if tick['low'] <= pos['sl']:
                            balance -= pos['risk_capital']
                            journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital']})
                            active_position = None
                            continue
                        elif tick['high'] >= pos['tp']:
                            balance += pos['risk_capital'] * self.target_rr
                            journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr})
                            active_position = None
                            continue
                    elif pos['direction'] == 'SHORT':
                        if tick['high'] >= pos['sl']:
                            balance -= pos['risk_capital']
                            journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital']})
                            active_position = None
                            continue
                        elif tick['low'] <= pos['tp']:
                            balance += pos['risk_capital'] * self.target_rr
                            journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr})
                            active_position = None
                            continue

                # --- TIMEFRAME STATE MATRIX ENGINE INTERFACE ---
                visible_state = sync_matrix.get_visible_state(current_time)
                htf_frame = visible_state['closed_htf']
                mtf_frame = visible_state['closed_mtf']
                
                if len(htf_frame) < 50 or len(mtf_frame) < 50:
                    continue
                    
                regime = MarketRegimeClassifier.classify_regime(htf_frame)
                if regime == "CHOPPY_RANGE":
                    continue
                    
                # Core high/low markers for pricing evaluation arrays
                htf_high, htf_low = htf_frame['high'].tail(30).max(), htf_frame['low'].tail(30).min()
                mtf_high, mtf_low = mtf_frame['high'].tail(30).max(), mtf_frame['low'].tail(30).min()
                
                equilibrium_4h = (htf_high + htf_low) / 2.0
                equilibrium_1h = (mtf_high + mtf_low) / 2.0
                
                mtf_fvgs = self.smc.identify_fair_value_gaps(mtf_frame)
                recent_ltf_window = sync_matrix.ltf.iloc[idx-8:idx]
                ltf_highs, ltf_lows = self.smc.evaluate_market_pivots(recent_ltf_window, window=2)
                
                # --- STRATEGY ARBITRAGE MUTATION SWITCH ENGINE ---
                is_long_setup = False
                is_short_setup = False
                
                if variant == 'APEX_ULTRA':
                    # Variant A Configuration: Strict macro 4H setups
                    if regime == "TRENDING_BULL" and current_price < equilibrium_4h:
                        if any(fvg['type'] == 'BULLISH' and fvg['top'] > current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_highs) > 0 and current_price > ltf_highs[-1]['price']:
                                is_long_setup = True
                    elif regime == "TRENDING_BEAR" and current_price > equilibrium_4h:
                        if any(fvg['type'] == 'BEARISH' and fvg['bottom'] < current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_lows) > 0 and current_price < ltf_lows[-1]['price']:
                                is_short_setup = True
                                
                elif variant == 'CORE_SHIFT':
                    # Variant B Configuration: Shift premium/discount line down to 1H frame for faster setups
                    if regime == "TRENDING_BULL" and current_price < equilibrium_1h:
                        if any(fvg['type'] == 'BULLISH' and fvg['top'] > current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_highs) > 0 and current_price > ltf_highs[-1]['price']:
                                is_long_setup = True
                    elif regime == "TRENDING_BEAR" and current_price > equilibrium_1h:
                        if any(fvg['type'] == 'BEARISH' and fvg['bottom'] < current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_lows) > 0 and current_price < ltf_lows[-1]['price']:
                                is_short_setup = True
                                
                elif variant == 'MOM_FLOW':
                    # Variant C Configuration: Remove premium/discount checks completely, trade direct momentum flow
                    if regime == "TRENDING_BULL":
                        if any(fvg['type'] == 'BULLISH' and fvg['top'] > current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_highs) > 0 and current_price > ltf_highs[-1]['price']:
                                is_long_setup = True
                    elif regime == "TRENDING_BEAR":
                        if any(fvg['type'] == 'BEARISH' and fvg['bottom'] < current_price for fvg in mtf_fvgs[-5:]):
                            if len(ltf_lows) > 0 and current_price < ltf_lows[-1]['price']:
                                is_short_setup = True
                                
                elif variant == 'SWEEP_ONLY':
                    # Variant D Configuration: Drop FVG rule, enter instantly on structural liquid sweeps + CHOCH
                    is_bull_sweep = mtf_frame['low'].iloc[-1] < mtf_frame['low'].iloc[-5: -1].min()
                    is_bear_sweep = mtf_frame['high'].iloc[-1] > mtf_frame['high'].iloc[-5: -1].max()
                    
                    if regime == "TRENDING_BULL" and is_bull_sweep:
                        if len(ltf_highs) > 0 and current_price > ltf_highs[-1]['price']:
                            is_long_setup = True
                    elif regime == "TRENDING_BEAR" and is_bear_sweep:
                        if len(ltf_lows) > 0 and current_price < ltf_lows[-1]['price']:
                            is_short_setup = True

                # --- EXECUTION TRIGGER ALLOCATION ---
                if is_long_setup and not active_position:
                    sl_price = tick['low'] * 0.995
                    size = self.risk_engine.calculate_position_size(balance, current_price, sl_price, self.instrument_config)
                    if size > 0:
                        active_position = {
                            'direction': 'LONG', 'sl': sl_price, 'risk_capital': size * abs(current_price - sl_price),
                            'tp': current_price + (abs(current_price - sl_price) * self.target_rr)
                        }
                elif is_short_setup and not active_position:
                    sl_price = tick['high'] * 1.005
                    size = self.risk_engine.calculate_position_size(balance, current_price, sl_price, self.instrument_config)
                    if size > 0:
                        active_position = {
                            'direction': 'SHORT', 'sl': sl_price, 'risk_capital': size * abs(sl_price - current_price),
                            'tp': current_price - (abs(sl_price - current_price) * self.target_rr)
                        }

            # --- PROCESS PERFORMANCE JOURNAL FOR LEADERBOARD ---
            if len(journal) > 0:
                df_j = pd.DataFrame(journal)
                t_trades = len(df_j)
                wins = len(df_j[df_j['status'] == 'WIN'])
                w_rate = (wins / t_trades) * 100
                t_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
                t_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
                p_factor = t_won / t_lost if t_lost > 0 else t_won
                
                leaderboard[variant] = {
                    'trades': t_trades, 'win_rate': f"{w_rate:.1f}%",
                    'profit_factor': f"{p_factor:.2f}", 'final_balance': f"${balance:,.2f}"
                }
            else:
                leaderboard[variant] = {'trades': 0, 'win_rate': '0.0%', 'profit_factor': '0.00', 'final_balance': f"${balance:,.2f}"}

        # --- OUTPUT INDUSTRIAL LEADERBOARD COMPARISON MATRIX ---
        print("\n==========================================================================")
        print("        👑 APEX QUANT OS v2: STRATEGY TOURNAMENT LEADERBOARD MATRIX")
        print("==========================================================================")
        print(f" {'STRATEGY VARIANT':17s} | {'TRADES':6s} | {'WIN RATE':8s} | {'PROFIT FACTOR':13s} | {'ENDING BALANCE':14s} |")
        print("--------------------------------------------------------------------------")
        for name, metrics in leaderboard.items():
            print(f" {name:17s} | {metrics['trades']:6d} | {metrics['win_rate']:8s} | {metrics['profit_factor']:13s} | {metrics['final_balance']:14s} |")
        print("==========================================================================")

if __name__ == "__main__":
    tournament = StrategyTournamentEngine()
    tournament.execute_tournament()
