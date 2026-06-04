import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.data_ingestion_v2 import HistoricalDataIngestorV2
from core.risk_engine_v2 import InstitutionalRiskEngine

class CoreShiftProductionStressTester:
    """
    Layer 6: Production Multi-Year Stress Testing Framework.
    Features hot-swappable direction toggles and parametric regime throttling
    to isolate true mathematical edges over millions of data points.
    """
    def __init__(self, symbol="BTCUSDT", initial_balance=10000.0, target_rr=4.0):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.target_rr = target_rr
        
        # --- PHASE 4 CORE CONFIGURATION NODES ---
        self.ALLOW_LONG = True       # Toggle to isolate the Long Core asset moats
        self.ALLOW_SHORT = False     # Hard kill switch on the toxic short-side pipeline
        self.REGIME_THROTTLE = 3.0   # Dropped from 4.5 to expand trade volume safely
        
        self.ingestor = HistoricalDataIngestorV2(self.symbol)
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def run_stress_test(self):
        print("==========================================================================")
        print(f" LAUNCHING ISOLATED MOAT VALIDATION RUN ON {self.symbol}")
        print(f" CONFIG: [LONG={self.ALLOW_LONG} | SHORT={self.ALLOW_SHORT} | THROTTLE={self.REGIME_THROTTLE}]")
        print("==========================================================================")
        
        matrices = self.ingestor.load_and_compile_matrix()
        df_15m = matrices['15m'].copy().sort_values('timestamp').reset_index(drop=True)
        df_1h = matrices['1h'].copy().sort_values('timestamp').reset_index(drop=True)
        df_4h = matrices['4h'].copy().sort_values('timestamp').reset_index(drop=True)
        
        # --- VECTORIZED METRIC CALCULATION ---
        df_4h['ema_20'] = df_4h['close'].ewm(span=20, adjust=False).mean()
        df_4h['ema_50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
        
        h_4h, l_4h, c_4h = df_4h['high'].to_numpy(), df_4h['low'].to_numpy(), df_4h['close'].to_numpy()
        tr = np.maximum(h_4h[1:] - l_4h[1:], np.maximum(abs(h_4h[1:] - c_4h[:-1]), abs(l_4h[1:] - c_4h[:-1])))
        tr = np.insert(tr, 0, h_4h[0] - l_4h[0])
        df_4h['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_4h['roll_high'] = df_4h['high'].rolling(window=14).max()
        df_4h['roll_low'] = df_4h['low'].rolling(window=14).min()
        df_4h['vol_ratio'] = (df_4h['roll_high'] - df_4h['roll_low']) / (df_4h['atr'] + 1e-8)
        
        df_4h['regime'] = "CHOPPY_RANGE"
        df_4h.loc[(df_4h['vol_ratio'] >= self.REGIME_THROTTLE) & (df_4h['close'] > df_4h['ema_20']) & (df_4h['ema_20'] > df_4h['ema_50']), 'regime'] = "TRENDING_BULL"
        df_4h.loc[(df_4h['vol_ratio'] >= self.REGIME_THROTTLE) & (df_4h['close'] < df_4h['ema_20']) & (df_4h['ema_20'] < df_4h['ema_50']), 'regime'] = "TRENDING_BEAR"

        df_1h['eq_high'] = df_1h['high'].rolling(30).max()
        df_1h['eq_low'] = df_1h['low'].rolling(30).min()
        df_1h['equilibrium'] = (df_1h['eq_high'] + df_1h['eq_low']) / 2.0
        
        df_1h['has_bull_fvg'] = False
        df_1h['has_bear_fvg'] = False
        h_1h, l_1h = df_1h['high'].to_numpy(), df_1h['low'].to_numpy()
        df_1h.iloc[2:, df_1h.columns.get_loc('has_bull_fvg')] = h_1h[:-2] < l_1h[2:]
        df_1h.iloc[2:, df_1h.columns.get_loc('has_bear_fvg')] = l_1h[:-2] > h_1h[2:]
        
        df_1h['any_bull_fvg_5'] = df_1h['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_1h['any_bear_fvg_5'] = df_1h['has_bear_fvg'].rolling(5).max().fillna(0).astype(bool)

        h_15m, l_15m = df_15m['high'].to_numpy(), df_15m['low'].to_numpy()
        df_15m['is_swing_high'] = False
        df_15m['is_swing_low'] = False
        
        for i in range(2, len(df_15m) - 2):
            if h_15m[i] > h_15m[i-1] and h_15m[i] > h_15m[i-2] and h_15m[i] >= h_15m[i+1] and h_15m[i] >= h_15m[i+2]:
                df_15m.at[i, 'is_swing_high'] = True
            if l_15m[i] < l_15m[i-1] and l_15m[i] < l_15m[i-2] and l_15m[i] <= l_15m[i+1] and l_15m[i] <= l_15m[i+2]:
                df_15m.at[i, 'is_swing_low'] = True
                
        df_15m['last_visible_sh'] = np.where(df_15m['is_swing_high'].shift(2), df_15m['high'].shift(2), np.nan)
        df_15m['last_visible_sl'] = np.where(df_15m['is_swing_low'].shift(2), df_15m['low'].shift(2), np.nan)
        df_15m['last_visible_sh'] = df_15m['last_visible_sh'].ffill()
        df_15m['last_visible_sl'] = df_15m['last_visible_sl'].ffill()

        # --- CHRONOLOGICAL TIMEFRAME POINTER ALIGNMENT ---
        ts_15m = df_15m['timestamp'].to_numpy()
        idx_4h = np.searchsorted(df_4h['timestamp'].to_numpy(), ts_15m, side='right') - 1
        idx_1h = np.searchsorted(df_1h['timestamp'].to_numpy(), ts_15m, side='right') - 1
        
        idx_4h = np.clip(idx_4h, 0, len(df_4h) - 1)
        idx_1h = np.clip(idx_1h, 0, len(df_1h) - 1)

        price_arr = df_15m['close'].to_numpy()
        high_arr = df_15m['high'].to_numpy()
        low_arr = df_15m['low'].to_numpy()
        
        regimes_4h = df_4h['regime'].to_numpy()[idx_4h]
        eq_1h = df_1h['equilibrium'].to_numpy()[idx_1h]
        bull_fvg_1h = df_1h['any_bull_fvg_5'].to_numpy()[idx_1h]
        bear_fvg_1h = df_1h['any_bear_fvg_5'].to_numpy()[idx_1h]
        
        ltf_sh = df_15m['last_visible_sh'].to_numpy()
        ltf_sl = df_15m['last_visible_sl'].to_numpy()

        # --- EXECUTION SIMULATION TUNNEL ---
        active_position = None
        journal = []
        peak_balance = self.balance
        max_drawdown_pct = 0.0
        
        for idx in range(100, len(df_15m)):
            current_price = price_arr[idx]
            current_high = high_arr[idx]
            current_low = low_arr[idx]
            
            if self.balance > peak_balance:
                peak_balance = self.balance
            current_dd = (peak_balance - self.balance) / peak_balance
            if current_dd > max_drawdown_pct:
                max_drawdown_pct = current_dd

            if active_position:
                pos = active_position
                if pos['direction'] == 'LONG':
                    if current_low <= pos['sl']:
                        self.balance -= pos['risk_capital']
                        journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital'], 'regime': pos['regime']})
                        active_position = None
                    elif current_high >= pos['tp']:
                        self.balance += pos['risk_capital'] * self.target_rr
                        journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr, 'regime': pos['regime']})
                        active_position = None
                elif pos['direction'] == 'SHORT':
                    if current_high >= pos['sl']:
                        self.balance -= pos['risk_capital']
                        journal.append({'status': 'LOSS', 'pnl': -pos['risk_capital'], 'regime': pos['regime']})
                        active_position = None
                    elif current_low <= pos['tp']:
                        self.balance += pos['risk_capital'] * self.target_rr
                        journal.append({'status': 'WIN', 'pnl': pos['risk_capital'] * self.target_rr, 'regime': pos['regime']})
                        active_position = None
                continue

            regime = regimes_4h[idx]
            if regime == "CHOPPY_RANGE":
                continue
                
            equilibrium = eq_1h[idx]
            
            if not active_position:
                # LONG TRACK (SWAPPABLE)
                if self.ALLOW_LONG and regime == "TRENDING_BULL" and current_price < equilibrium:
                    if bull_fvg_1h[idx] and not np.isnan(ltf_sh[idx]) and current_price > ltf_sh[idx]:
                        sl_price = current_low * 0.995
                        size = self.risk_engine.calculate_position_size(self.balance, current_price, sl_price, self.instrument_config)
                        if size > 0:
                            active_position = {
                                'direction': 'LONG', 'sl': sl_price, 'risk_capital': size * (current_price - sl_price),
                                'tp': current_price + ((current_price - sl_price) * self.target_rr), 'regime': regime
                            }
                # SHORT TRACK (SWAPPABLE)           
                elif self.ALLOW_SHORT and regime == "TRENDING_BEAR" and current_price > equilibrium:
                    if bear_fvg_1h[idx] and not np.isnan(ltf_sl[idx]) and current_price < ltf_sl[idx]:
                        sl_price = current_high * 1.005
                        size = self.risk_engine.calculate_position_size(self.balance, current_price, sl_price, self.instrument_config)
                        if size > 0:
                            active_position = {
                                'direction': 'SHORT', 'sl': sl_price, 'risk_capital': size * (sl_price - current_price),
                                'tp': current_price - ((sl_price - current_price) * self.target_rr), 'regime': regime
                            }

        # --- QUANTITATIVE ANALYSIS READOUT ---
        print("\n==========================================================================")
        print("        🏁 LONG-HORIZON PRODUCTION READOUT MATRIX")
        print("==========================================================================")
        
        if len(journal) == 0:
            print("[⚠️ NOTICE] Strategy rules generated 0 trades. Review parametric filters.")
            return
            
        df_j = pd.DataFrame(journal)
        total_trades = len(df_j)
        wins = len(df_j[df_j['status'] == 'WIN'])
        losses = len(df_j[df_j['status'] == 'LOSS'])
        win_rate = (wins / total_trades) * 100
        
        total_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
        total_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
        profit_factor = total_won / total_lost if total_lost > 0 else total_won
        
        print(f"  📈 Initial Inception Balance: $ {self.initial_balance:,.2f}")
        print(f"  📉 Terminal Balance Output:   $ {self.balance:,.2f}")
        print(f"  🏁 Total Stress-Test Trades:  {total_trades}")
        print(f"  🎯 Empirical Win Rate Matrix: {win_rate:.2f}% (W: {wins} | L: {losses})")
        print(f"  📊 Final System Profit Factor: {profit_factor:.2f}")
        print(f"  ⚠️ Maximum Geometric Drawdown: {max_drawdown_pct * 100:.2f}%")
        print("==========================================================================")

if __name__ == "__main__":
    tester = CoreShiftProductionStressTester()
    tester.run_stress_test()
