import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class WalkForwardValidator:
    """
    Layer 6.9: Institutional Walk-Forward Structural Verification Engine.
    Isolates parametric optimization within In-Sample epochs (2024-2025)
    and validates forward expectancy on Out-of-Sample frontiers (2026).
    """
    def __init__(self, initial_balance=10000.0):
        self.initial_balance = initial_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_signal_arrays(self, symbol):
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

        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)
        
        df_htf['regime'] = "CHOPPY_RANGE"
        df_htf.loc[(df_htf['vol_ratio'] >= 3.0) & (df_htf['close'] > df_htf['ema_20']) & (df_htf['ema_20'] > df_htf['ema_50']), 'regime'] = "TRENDING_BULL"

        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)

        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['regime_htf'] = df_htf['regime'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        
        return df_ltf

    def simulate_epoch(self, df_ltf, target_rr, target_years):
        """
        Simulates strategy executions restricted explicitly to specified calendar years.
        """
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        regimes = df_ltf['regime_htf'].to_numpy()
        equilibriums = df_ltf['eq_mtf'].to_numpy()
        fvgs = df_ltf['bull_fvg_mtf'].to_numpy()
        sh_arr = df_ltf['last_visible_sh'].to_numpy()
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
            current_dd = (peak - balance) / peak
            if current_dd > max_dd:
                max_dd = current_dd

            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    risk = balance * 0.01
                    balance -= risk
                    journal.append({'status': 'LOSS', 'pnl': -risk})
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    risk = balance * 0.01
                    balance += risk * target_rr
                    journal.append({'status': 'WIN', 'pnl': risk * target_rr})
                    active_pos = None
                continue

            if regimes[idx] == "TRENDING_BULL" and price_arr[idx] < equilibriums[idx]:
                if fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                    sl = low_arr[idx] * 0.995
                    tp = price_arr[idx] + ((price_arr[idx] - sl) * target_rr)
                    active_pos = {'sl': sl, 'tp': tp}

        if not journal:
            return 0, 0.00, 0.00
            
        df_j = pd.DataFrame(journal)
        total_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
        total_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
        pf = total_won / total_lost if total_lost > 0 else total_won
        wins = len(df_j[df_j['status'] == 'WIN'])
        
        return len(df_j), pf, max_dd * 100

    def run_validation_pipeline(self):
        print("==========================================================================")
        print(" INITIALIZING LONG-HORIZON WALK-FORWARD CRITICAL VALIDATION ENGINE")
        print("==========================================================================")
        
        assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        rr_sweep = [2.0, 2.5, 3.0, 3.5, 4.0]
        
        print("[*] Training Session Active: Mapping In-Sample Bounds (2024-2025)...")
        
        for asset in assets:
            print(f"\n--------------------------------------------------------------------------")
            print(f" 🔬 ASSET RUN ANALYSIS: {asset}")
            print(f"--------------------------------------------------------------------------")
            df_signals = self.generate_signal_arrays(asset)
            
            # --- PHASE 1: IN-SAMPLE OPTIMIZATION SWEEP ---
            best_is_rr = 2.0
            best_is_pf = 0.0
            
            print("  [STEP 1: IN-SAMPLE PARALLEL SWEEP (2024-2025)]")
            for rr in rr_sweep:
                trades, pf, dd = self.simulate_epoch(df_signals, rr, [2024, 2025])
                print(f"    ├── Target RR 1:{rr:<3} | Trades: {trades:2d} | In-Sample PF: {pf:.2f} | Max DD: {dd:.1f}%")
                if pf > best_is_pf:
                    best_is_pf = pf
                    best_is_rr = rr
                    
            print(f"  [✓] IN-SAMPLE TRAINING ANCHOR SECURED:")
            print(f"    └── Peak Performing Vector Target: 1:{best_is_rr} RR (PF: {best_is_pf:.2f})")
            
            # --- PHASE 2: OUT-OF-SAMPLE LOCK & FORWARD PASS ---
            print(f"\n  [STEP 2: FREEZING PARAMETERS & FORWARDING PASS TO OOS FRONTIER (2026)]")
            oos_trades, oos_pf, oos_dd = self.simulate_epoch(df_signals, best_is_rr, [2026])
            
            print(f"    🔥 2026 OUT-OF-SAMPLE VERDICT METRIC READOUT:")
            print(f"      ├── Executed Frontier Trades: {oos_trades}")
            print(f"      ├── Frozen Vector Target     : 1:{best_is_rr} RR")
            print(f"      ├── Forward Profit Factor    : {oos_pf:.2f}")
            print(f"      └── Forward Peak Drawdown   : {oos_dd:.1f}%")
            
            if oos_pf >= 1.20:
                print("    🟢 [VERDICT: ALPHA VALIDATED] Edge generalizes out-of-sample.")
            elif oos_pf >= 1.00:
                print("    🟡 [VERDICT: FRAGILE EDGE] Weak survival capacity. Monitor churn.")
            else:
                print("    🔴 [VERDICT: REJECTION] Parametric decay detected. Optimization was an artifact.")
        print("==========================================================================")

if __name__ == "__main__":
    validator = WalkForwardValidator()
    validator.run_validation_pipeline()
