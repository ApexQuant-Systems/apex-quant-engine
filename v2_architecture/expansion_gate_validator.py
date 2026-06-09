import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class ExpansionGateValidator:
    """
    Layer 7.2: Specialized Volatility Activation Gate Validator.
    Executes a side-by-side comparative walk-forward verification (2024-2025 vs 2026)
    to mathematically prove the efficacy of a macro volatility expansion filter.
    """
    def __init__(self, initial_balance=10000.0):
        self.initial_balance = initial_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_base_signals(self, symbol):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # 4H Volatility Vector Calculations
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr_htf = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr_htf = np.insert(tr_htf, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr_htf).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        # 1H Micro-Structure
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        # 15M Entry Core
        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['macro_vol_ratio'] = df_htf['vol_ratio'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]
        
        return df_ltf

    def backtest_stream(self, df_ltf, use_vol_filter, target_years):
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios = df_ltf['macro_vol_ratio'].to_numpy()
        equilibriums = df_ltf['eq_mtf'].to_numpy()
        fvgs = df_ltf['bull_fvg_mtf'].to_numpy()
        sh_arr = df_ltf['last_visible_sh'].to_numpy()
        liq_arr = df_ltf['struct_liq_mapped'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        journal = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if years_arr[idx] not in target_years:
                continue
                
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak
            if dd > max_dd:
                max_dd = dd

            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    risk = balance * 0.01
                    balance -= risk
                    journal.append({'pnl': -risk})
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    risk = balance * 0.01
                    balance += risk * active_pos['computed_rr']
                    journal.append({'pnl': risk * active_pos['computed_rr']})
                    active_pos = None
                continue

            # Volatility Gate Evaluation Intercept
            if use_vol_filter and vol_ratios[idx] < 3.0:
                continue # Lock execution to cash during compressed range environments

            if price_arr[idx] <  equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                sl = low_arr[idx] * 0.995
                risk_distance = price_arr[idx] - sl
                if risk_distance <= 0:
                    continue
                tp = liq_arr[idx]
                computed_rr = (tp - price_arr[idx]) / risk_distance
                if computed_rr < 1.5:
                    continue

                active_pos = {'sl': sl, 'tp': tp, 'computed_rr': computed_rr}

        if not journal:
            return 0, 0.00, 0.00
            
        df_j = pd.DataFrame(journal)
        total_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
        total_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
        pf = total_won / total_lost if total_lost > 0 else total_won
        
        return len(df_j), pf, max_dd * 100

    def run_comparative_matrix(self):
        print("==========================================================================================")
        print("         👑 APEX QUANT OS V2: VOLATILITY ACTIVATION WALK-FORWARD VERIFIER")
        print("==========================================================================================")
        
        assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        for asset in assets:
            print(f"\n[🔬 TESTING MATRIX NODE: {asset}]")
            df_signals = self.generate_base_signals(asset)
            
            # --- RUN CONTROL TRACK (NO FILTER) ---
            is_tr_c, is_pf_c, is_dd_c = self.backtest_stream(df_signals, use_vol_filter=False, target_years=[2024, 2025])
            oos_tr_c, oos_pf_c, oos_dd_c = self.backtest_stream(df_signals, use_vol_filter=False, target_years=[2026])
            
            # --- RUN EXPERIMENTAL TRACK (WITH VOL FILTER) ---
            is_tr_f, is_pf_f, is_dd_f = self.backtest_stream(df_signals, use_vol_filter=True, target_years=[2024, 2025])
            oos_tr_f, oos_pf_f, oos_dd_f = self.backtest_stream(df_signals, use_vol_filter=True, target_years=[2026])
            
            print(f"  ├── CONTROL ROAD (UNFILTERED):")
            print(f"  │     ├── In-Sample  (2024-2025) : {is_tr_c:2d} Trades | Profit Factor: {is_pf_c:.2f} | Max DD: {is_dd_c:.1f}%")
            print(f"  │     └── Out-Sample (2026)      : {oos_tr_c:2d} Trades | Profit Factor: {oos_pf_c:.2f} | Max DD: {oos_dd_c:.1f}%")
            print(f"  │")
            print(f"  └── VOLATILITY GATED ROAD (FILTERED):")
            print(f"        ├── In-Sample  (2024-2025) : {is_tr_f:2d} Trades | Profit Factor: {is_pf_f:.2f} | Max DD: {is_dd_f:.1f}%")
            
            verdict = "🟢 [ALPHA SECURED] OOS Profit Factor Expanded." if oos_pf_f > oos_pf_c else "🔴 [DECAY REJECTION] Filter induced curve-fitting drop."
            print(f"        └── Out-Sample (2026)      : {oos_tr_f:2d} Trades | Profit Factor: {oos_pf_f:.2f} | Max DD: {oos_dd_f:.1f}% -> {verdict}")
        print("==========================================================================================")

if __name__ == "__main__":
    validator = ExpansionGateValidator()
    validator.run_comparative_matrix()
