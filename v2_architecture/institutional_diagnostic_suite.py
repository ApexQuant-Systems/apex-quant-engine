import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class InstitutionalDiagnosticSuite:
    """
    Layer 8.0: Multi-Track Systemic Diagnostic and Validation Platform.
    Executes BTC Monte Carlo/Rolling pass, ETH MAE/MFE stop-distance deep sweeps,
    and the SOL Pullback vs Momentum structural experiment.
    """
    def __init__(self, initial_balance=10000.0):
        self.initial_balance = initial_balance

    def load_clean_data(self, symbol):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Deep archive missing for: {raw_path}")
        df = pd.read_csv(raw_path)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.sort_values('datetime').set_index('datetime')
        return df

    def resample_and_compute_metrics(self, df_raw):
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # Volatility & Trend Channels
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        # Micro-Structure Anchors
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = df_mtf['high'].shift(2) < df_mtf['low']
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        # LTF Swing Point Extraction
        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        # Alignment
        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['macro_vol_ratio'] = df_htf['vol_ratio'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]
        
        return df_ltf

    def run_btc_advanced_validation(self):
        print("\n==========================================================================")
        print(" TRACK A: ADVANCED CORE STRUCTURAL VERIFICATION (BTCUSDT)")
        print("==========================================================================")
        df_raw = self.load_clean_data("BTCUSDT")
        df_ltf = self.resample_and_compute_metrics(df_raw)
        
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios, equilibriums = df_ltf['macro_vol_ratio'].to_numpy(), df_ltf['eq_mtf'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        realized_returns = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    realized_returns.append(-1.0)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    realized_returns.append(active_pos['computed_rr'])
                    active_pos = None
                continue

            if vol_ratios[idx] >= 3.0 and price_arr[idx] < equilibriums[idx]:
                if fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                    sl = low_arr[idx] * 0.995
                    risk_distance = price_arr[idx] - sl
                    if risk_distance <= 0: continue
                    tp = liq_arr[idx]
                    computed_rr = (tp - price_arr[idx]) / risk_distance
                    if computed_rr < 1.5: continue
                    active_pos = {'sl': sl, 'tp': tp, 'computed_rr': computed_rr}

        if not realized_returns:
            print("[🛑 ERROR] Realized transaction stream empty.")
            return

        # 1. MONTE CARLO SIMULATION CORE
        print("[*] Launching 1,000-Iteration Bootstrap Monte Carlo Sequence Shuffle...")
        mc_drawdowns = []
        mc_winrates = []
        
        for _ in range(1000):
            shuffle_seq = np.random.choice(realized_returns, size=len(realized_returns), replace=True)
            bal = 10000.0
            pk = bal
            m_dd = 0.0
            w_count = 0
            
            for ret in shuffle_seq:
                risk = bal * 0.01
                bal += risk * ret
                if bal > pk: pk = bal
                dd = (pk - bal) / pk
                if dd > m_dd: m_dd = dd
                if ret > 0: w_count += 1
                
            mc_drawdowns.append(m_dd * 100)
            mc_winrates.append((w_count / len(shuffle_seq)) * 100)

        print(f"  ├── realized Sample Size    : {len(realized_returns)} Total Trades")
        print(f"  ├── Median Simulated Winrate: {np.median(mc_winrates):.2f}%")
        print(f"  ├── Median Monte Carlo DD   : {np.median(mc_drawdowns):.2f}%")
        print(f"  └── 95th Percentile Max DD  : {np.percentile(mc_drawdowns, 95):.2f}% (Tail Risk Boundary)")

    def run_eth_footprint_matrix(self):
        print("\n==========================================================================")
        print(" TRACK B: DISCRETE GEOMETRIC EXECUTION SWEEP (ETHUSDT OUT-OF-SAMPLE)")
        print("==========================================================================")
        df_raw = self.load_clean_data("ETHUSDT")
        df_ltf = self.resample_and_compute_metrics(df_raw)
        
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios, equilibriums = df_ltf['macro_vol_ratio'].to_numpy(), df_ltf['eq_mtf'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        stop_pads = [0.995, 0.9925, 0.990, 0.9875, 0.985]
        exit_modes = ['1.5', '2.0', '2.5', '3.0', 'STRUCTURE']

        print(f" {'STOP DIST':9s} | " + " | ".join([f" TARGET: {m:9s} " for m in exit_modes]) + " |")
        print("--------------------------------------------------------------------------")

        for pad in stop_pads:
            row_str = f" SL: {pad:.4f} |"
            for mode in exit_modes:
                # Execution simulation pass restricted strictly to 2026 Out-of-Sample frontier
                bal = 10000.0
                active_pos = None
                journal = []
                
                for idx in range(100, len(df_ltf)):
                    if years_arr[idx] != 2026: continue
                    if vol_ratios[idx] < 3.0: continue

                    if active_pos:
                        if low_arr[idx] <= active_pos['sl']:
                            risk = bal * 0.01
                            bal -= risk
                            journal.append(-risk)
                            active_pos = None
                        elif high_arr[idx] >= active_pos['tp']:
                            risk = bal * 0.01
                            bal += risk * active_pos['computed_rr']
                            journal.append(risk * active_pos['computed_rr'])
                            active_pos = None
                        continue

                    if price_arr[idx] < equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                        sl = low_arr[idx] * pad
                        risk_dist = price_arr[idx] - sl
                        if risk_dist <= 0: continue
                        
                        if mode == 'STRUCTURE':
                            tp = liq_arr[idx]
                            computed_rr = (tp - price_arr[idx]) / risk_dist
                        else:
                            computed_rr = float(mode)
                            tp = price_arr[idx] + (risk_dist * computed_rr)
                            
                        if computed_rr < 1.5: continue
                        active_pos = {'sl': sl, 'tp': tp, 'computed_rr': computed_rr}

                if not journal:
                    row_str += f" {'DORMANT':17s} |"
                else:
                    won = sum([p for p in journal if p > 0])
                    lost = abs(sum([p for p in journal if p < 0]))
                    pf = won / lost if lost > 0 else won
                    icon = "🟢" if pf >= 1.15 else ("🔴" if pf < 1.0 else "完")
                    row_str += f" {len(journal):2d}Tr/{pf:4.2f} {icon} |"
            print(row_str)
            print("--------------------------------------------------------------------------")

    def run_sol_regime_tournament(self):
        print("\n==========================================================================")
        print(" TRACK C: STRUCTURAL STYLE TOURNAMENT (SOLUSDT OUT-OF-SAMPLE)")
        print("==========================================================================")
        df_raw = self.load_clean_data("SOLUSDT")
        df_ltf = self.resample_and_compute_metrics(df_raw)
        
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios, equilibriums = df_ltf['macro_vol_ratio'].to_numpy(), df_ltf['eq_mtf'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        for style in ['PULLBACK_DISCOUNT', 'MOMENTUM_BREAKOUT']:
            bal = 10000.0
            active_pos = None
            journal = []

            for idx in range(100, len(df_ltf)):
                if years_arr[idx] != 2026: continue
                if vol_ratios[idx] < 3.0: continue # Verify inside volatility expansion regimes

                if active_pos:
                    if low_arr[idx] <= active_pos['sl']:
                        risk = bal * 0.01; bal -= risk; journal.append(-risk); active_pos = None
                    elif high_arr[idx] >= active_pos['tp']:
                        risk = bal * 0.01; bal += risk * 3.0; journal.append(risk * 3.0); active_pos = None
                    continue

                # Style Branch Intercept
                if style == 'PULLBACK_DISCOUNT':
                    # Entry strictly conditioned on deep structural pullbacks into a discount zone
                    condition = price_arr[idx] < equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]
                else:
                    # Entry conditioned on momentum breakout scaling completely ABOVE the micro-structure range high ceiling
                    condition = price_arr[idx] > liq_arr[idx] and vol_ratios[idx] >= 3.5

                if condition:
                    sl = low_arr[idx] * 0.990 # Fixed structural baseline padding
                    risk_dist = abs(price_arr[idx] - sl)
                    if risk_dist <= 0: continue
                    tp = price_arr[idx] + (risk_dist * 3.0) # Unified reference target baseline
                    active_pos = {'sl': sl, 'tp': tp, 'computed_rr': 3.0}

            won = sum([p for p in journal if p > 0])
            lost = abs(sum([p for p in journal if p < 0]))
            pf = won / lost if lost > 0 else won
            print(f"  ├── STYLE CONFIGURATION: {style:19s} | Trades: {len(journal):3d} | 2026 OOS Profit Factor: {pf:.2f}")

        print("==========================================================================")

if __name__ == "__main__":
    suite = InstitutionalDiagnosticSuite()
    suite.run_btc_advanced_validation()
    suite.run_eth_footprint_matrix()
    suite.run_sol_regime_tournament()
