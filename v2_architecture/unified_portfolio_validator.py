import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class UnifiedPortfolioValidator:
    """
    Layer 9.2: Enterprise Portfolio Aggregator & Validation Core.
    Bypasses integer time serialization by binding explicit ISO date strings 
    directly to trade objects, unlocking un-aliased asset covariance metrics.
    """
    def __init__(self, initial_balance=30000.0):
        self.initial_balance = initial_balance
        self.assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def extract_cartridge_trades(self, symbol):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing absolute data track: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # Volatility Vectors
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        # Micro-Structure Target Map
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = df_mtf['high'].shift(2) < df_mtf['low']
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        # LTF Execution Plane
        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        # PATCHED: Decoupled NumPy statement from Pandas forward-fill function
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['macro_vol_ratio'] = df_htf['vol_ratio'].to_numpy()[idx_htf]
        df_ltf['macro_close'] = df_htf['close'].to_numpy()[idx_htf]
        df_ltf['macro_ema_20'] = df_htf['ema_20'].to_numpy()[idx_htf]
        df_ltf['macro_ema_50'] = df_htf['ema_50'].to_numpy()[idx_htf]
        
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]

        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios, equilibriums = df_ltf['macro_vol_ratio'].to_numpy(), df_ltf['eq_mtf'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()
        m_closes, e20, e50 = df_ltf['macro_close'].to_numpy(), df_ltf['macro_ema_20'].to_numpy(), df_ltf['macro_ema_50'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()
        
        date_str_arr = df_ltf['datetime'].dt.strftime('%Y-%m-%d').to_numpy()
        time_arr = df_ltf['timestamp'].to_numpy()

        trades = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    active_pos['exit_date'] = date_str_arr[idx]
                    active_pos['exit_timestamp'] = int(time_arr[idx])
                    active_pos['risk_mult'] = -1.0
                    trades.append(active_pos)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    active_pos['exit_date'] = date_str_arr[idx]
                    active_pos['exit_timestamp'] = int(time_arr[idx])
                    active_pos['risk_mult'] = float(active_pos['computed_rr'])
                    trades.append(active_pos)
                    active_pos = None
                continue

            if symbol == 'BTCUSDT':
                if vol_ratios[idx] < 3.0: continue
                condition = price_arr[idx] < equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]
                sl_pad, rr_mode = 0.995, 'STRUCTURE'
            elif symbol == 'ETHUSDT':
                if vol_ratios[idx] < 3.0: continue
                condition = price_arr[idx] < equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]
                sl_pad, rr_mode = 0.990, 2.5
            elif symbol == 'SOLUSDT':
                if vol_ratios[idx] < 3.5: continue
                condition = price_arr[idx] > liq_arr[idx]
                sl_pad, rr_mode = 0.990, 3.0

            if condition:
                sl = low_arr[idx] * sl_pad
                risk_dist = abs(price_arr[idx] - sl)
                if risk_dist <= 0: continue
                
                if rr_mode == 'STRUCTURE':
                    tp = liq_arr[idx]
                    computed_rr = (tp - price_arr[idx]) / risk_dist
                else:
                    computed_rr = float(rr_mode)
                    tp = price_arr[idx] + (risk_dist * computed_rr)

                if computed_rr < 1.5: continue

                if vol_ratios[idx] >= 3.0 and m_closes[idx] > e20[idx] and e20[idx] > e50[idx]:
                    regime_tag = 'BULL_EXPANSION'
                elif vol_ratios[idx] >= 3.0 and m_closes[idx] < e20[idx] and e20[idx] < e50[idx]:
                    regime_tag = 'BEAR_EXPANSION'
                else:
                    regime_tag = 'COMPRESSED_RANGE'

                active_pos = {
                    'asset': symbol, 'exit_date': None, 'exit_timestamp': 0,
                    'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0,
                    'regime': regime_tag, 'year': int(years_arr[idx])
                }
        return trades

    def execute_timeline_simulation(self, global_ledger, weights, initial_bal, target_years):
        balance = initial_bal
        peak = balance
        max_dd = 0.0
        wins, losses = 0, 0
        total_pnl_won, total_pnl_lost = 0.0, 0.0

        for trade in global_ledger:
            if trade['year'] not in target_years: continue

            if balance > peak: peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd: max_dd = current_dd

            if current_dd >= 0.25: risk_scale = 0.0000
            elif current_dd >= 0.20: risk_scale = 0.0025
            elif current_dd >= 0.15: risk_scale = 0.0050
            elif current_dd >= 0.10: risk_scale = 0.0075
            else: risk_scale = 0.0100

            asset_weight = weights.get(trade['asset'], 0.0)
            risk_capital = balance * risk_scale * asset_weight
            trade_pnl = risk_capital * trade['risk_mult']
            balance += trade_pnl

            if trade_pnl != 0:
                if trade['risk_mult'] > 0:
                    wins += 1; total_pnl_won += trade_pnl
                else:
                    losses += 1; total_pnl_lost += abs(trade_pnl)

        total_trades = wins + losses
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        pf = total_pnl_won / total_pnl_lost if total_pnl_lost > 0 else total_pnl_won
        recovery_factor = (balance - initial_bal) / (initial_bal * max_dd + 1e-8)

        return total_trades, win_rate, pf, max_dd * 100, balance, recovery_factor

    def run_portfolio_analysis_suite(self):
        print("==========================================================================================")
        print(" 🔥 APEX QUANT OS V2: PRODUCTION INTEGRATED PORTFOLIO COMMAND SUITE")
        print("==========================================================================================")
        
        master_vault = {}
        global_ledger = []
        for asset in self.assets:
            print(f"[*] Ingesting pure token array signals for Cartridge: {asset}...")
            master_vault[asset] = self.extract_cartridge_trades(asset)
            global_ledger.extend(master_vault[asset])

        global_ledger = sorted(global_ledger, key=lambda x: x['exit_timestamp'])

        # --- TEST 1: UNIFIED EQUITY FRONTIER ---
        print("\n[TEST 1: UNIFIED PORTFOLIO WALK-FORWARD EQUITY FRONTIER]")
        equal_weights = {"BTCUSDT": 1.0, "ETHUSDT": 1.0, "SOLUSDT": 1.0}
        is_t, is_wr, is_pf, is_dd, is_bal, is_rf = self.execute_timeline_simulation(global_ledger, equal_weights, self.initial_balance, [2024, 2025])
        oos_t, oos_wr, oos_pf, oos_dd, oos_bal, oos_rf = self.execute_timeline_simulation(global_ledger, equal_weights, self.initial_balance, [2026])
        print(f"  ├── In-Sample Epoch  (2024-2025) : {is_t:3d} Active Trades | WR: {is_wr:4.1f}% | PF: {is_pf:.2f} | Max DD: {is_dd:4.1f}% | PnL: ${(is_bal-self.initial_balance):+,.2f}")
        print(f"  └── Out-of-Sample Frontier (2026) : {oos_t:3d} Active Trades | WR: {oos_wr:4.1f}% | PF: {oos_pf:.2f} | Max DD: {oos_dd:4.1f}% | PnL: ${(oos_bal-self.initial_balance):+,.2f}")

        # --- TEST 2: FIXED INTER-ASSET COVARIANCE CORRELATION MATRIX ---
        print("\n[TEST 2: FIXED INTER-ASSET ALPHA RETURN CORRELATION MATRIX]")
        series_dict = {}
        for asset in self.assets:
            sub_trades = master_vault[asset]
            if sub_trades:
                df_sub = pd.DataFrame(sub_trades)
                series_dict[asset] = df_sub.groupby('exit_date')['risk_mult'].sum()
            else:
                series_dict[asset] = pd.Series(dtype=float)

        df_corr = pd.DataFrame(series_dict).fillna(0.0)
        print(df_corr.corr().to_string())

        # --- TEST 3: ALLOCATION TOURNAMENT ---
        print("\n[TEST 3: CAPITAL ALLOCATION STRATEGY TOURNAMENT (2026 OUT-OF-SAMPLE)]")
        tournaments = {
            "Portfolio A (100% BTC Anchor)": {"BTCUSDT": 1.0, "ETHUSDT": 0.0, "SOLUSDT": 0.0},
            "Portfolio B (50% BTC / 25% Mix)": {"BTCUSDT": 0.5, "ETHUSDT": 0.25, "SOLUSDT": 0.25},
            "Portfolio C (40% BTC / 30% Mix)": {"BTCUSDT": 0.4, "ETHUSDT": 0.30, "SOLUSDT": 0.30},
            "Portfolio D (Pure Risk Parity Equal)": {"BTCUSDT": 0.33, "ETHUSDT": 0.33, "SOLUSDT": 0.33}
        }
        for name, w_grid in tournaments.items():
            t, wr, pf, dd, bal, rf = self.execute_timeline_simulation(global_ledger, w_grid, self.initial_balance, [2026])
            print(f"  ├── {name:36s} -> Active Trades: {t:3d} | PF: {pf:.2f} | Max DD: {dd:4.1f}% | Recovery Factor: {rf:.2f}")

        # --- TEST 4: GLOBAL REGIME INTERCEPT ---
        print("\n[TEST 4: REGIME ATTRIBUTION EXPECTANCY INTERCEPT]")
        df_global = pd.DataFrame(global_ledger)
        print(f" {'REGIME STATE':18s} | {'TRADES':6s} | {'COMBINED PROFIT FACTOR':22s} | {'EXPECTANCY':10s} |")
        print("------------------------------------------------------------------------------------------")
        for regime in ['BULL_EXPANSION', 'BEAR_EXPANSION', 'COMPRESSED_RANGE']:
            sub = df_global[df_global['regime'] == regime]
            if sub.empty: continue
            r_won = sub[sub['risk_mult'] > 0]['risk_mult'].sum()
            r_lost = abs(sub[sub['risk_mult'] < 0]['risk_mult'].sum())
            r_pf = r_won / r_lost if r_lost > 0 else r_won
            print(f"  ├── {regime:14s} | {len(sub):5d}  | PF: {r_pf:20.2f}  | {sub['risk_mult'].mean():+8.2f}R  |")

        # --- TEST 5: PORTFOLIO MONTE CARLO ---
        print("\n[TEST 5: CROSS-ASSET PORTFOLIO BOOTSTRAP MONTE CARLO (1,000 ITERATIONS)]")
        mc_dd = []
        for _ in range(1000):
            shuffle_seq = [global_ledger[i] for i in np.random.choice(len(global_ledger), size=len(global_ledger), replace=True)]
            _, _, _, dd, _, _ = self.execute_timeline_simulation(shuffle_seq, equal_weights, self.initial_balance, [2024, 2025, 2026])
            mc_dd.append(dd)
            
        print(f"  ├── Integrated Portfolio Pool           : {len(global_ledger)} Combined Trades")
        print(f"  ├── Median Simulated Portfolio Drawdown  : {np.median(mc_dd):.2f}%")
        print(f"  └── 95th Percentile Tail Risk DD Boundary: {np.percentile(mc_dd, 95):.2f}% 🛡️")
        print("==========================================================================================")

if __name__ == "__main__":
    center = UnifiedPortfolioValidator()
    center.run_portfolio_analysis_suite()
