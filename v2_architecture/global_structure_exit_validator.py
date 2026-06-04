import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class GlobalStructureExitValidator:
    """
    Layer 7: Global Cross-Asset Structural Exit Verification Framework.
    Locks entries and structural liquidity exit rules entirely in-sample (2024-2025)
    and tests robustness out-of-sample (2026) across BTC, ETH, and SOL.
    """
    def __init__(self, initial_balance=10000.0):
        self.initial_balance = initial_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def process_asset_signals(self, symbol):
        """
        Extracts multi-timeframe vector fields and maps the structural liquidity target array.
        """
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing deep archive path for asset: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # HTF Regime Filters
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr_htf = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr_htf = np.insert(tr_htf, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr_htf).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)
        
        df_htf['regime'] = "CHOPPY_RANGE"
        df_htf.loc[(df_htf['vol_ratio'] >= 3.0) & (df_htf['close'] > df_htf['ema_20']) & (df_htf['ema_20'] > df_htf['ema_50']), 'regime'] = "TRENDING_BULL"

        # MTF Setup Layer
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        # LTF Entry Generation
        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['regime_htf'] = df_htf['regime'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]
        
        return df_ltf

    def execute_validation_pass(self, df_ltf, target_years):
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        regimes = df_ltf['regime_htf'].to_numpy()
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
                    journal.append({'status': 'LOSS', 'pnl': -risk})
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    risk = balance * 0.01
                    pnl_gain = risk * active_pos['computed_rr']
                    balance += pnl_gain
                    journal.append({'status': 'WIN', 'pnl': pnl_gain})
                    active_pos = None
                continue

            if regimes[idx] == "TRENDING_BULL" and price_arr[idx] < equilibriums[idx]:
                if fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                    sl = low_arr[idx] * 0.995
                    risk_distance = price_arr[idx] - sl
                    if risk_distance <= 0:
                        continue
                        
                    tp = liq_arr[idx]
                    computed_rr = (tp - price_arr[idx]) / risk_distance
                    if computed_rr < 1.5: # Hard institutional execution threshold
                        continue

                    active_pos = {'sl': sl, 'tp': tp, 'computed_rr': computed_rr}

        if not journal:
            return 0, 0.00, 0.00
            
        df_j = pd.DataFrame(journal)
        total_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
        total_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
        pf = total_won / total_lost if total_lost > 0 else total_won
        wins = len(df_j[df_j['status'] == 'WIN'])
        wr = (wins / len(df_j)) * 100
        
        return len(df_j), wr, pf, max_dd * 100

    def run_global_verification(self):
        print("==========================================================================")
        print(" APEX QUANT OS V2: GLOBAL CROSS-ASSET STRUCTURAL VALIDATION ENGINE")
        print("==========================================================================")
        
        assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        for asset in assets:
            print(f"\n[🔬 ANALYZING CROSS-ASSET NODE: {asset}]")
            try:
                df_signals = self.process_asset_signals(asset)
                
                # In-Sample Execution Pass (2024-2025)
                is_trades, is_wr, is_pf, is_dd = self.execute_validation_pass(df_signals, [2024, 2025])
                print(f"  ├── In-Sample (2024-2025)  : {is_trades:2d} Trades | WR: {is_wr:4.1f}% | Profit Factor: {is_pf:.2f} | Max DD: {is_dd:4.1f}%")
                
                # Out-of-Sample Validation Frontier Pass (2026)
                oos_trades, oos_wr, oos_pf, oos_dd = self.execute_validation_pass(df_signals, [2026])
                
                verdict_icon = "🟢 [VALIDATED GLOBAL EDGE]" if oos_pf >= 1.15 and is_pf >= 1.0 else (
                    "🟡 [ASSET-SPECIFIC Baseline]" if oos_pf >= 1.0 else "🔴 [STRATEGY REJECTED]"
                )
                print(f"  └── Out-of-Sample (2026)   : {oos_trades:2d} Trades | WR: {oos_wr:4.1f}% | Profit Factor: {oos_pf:.2f} | Max DD: {oos_dd:4.1f}% -> {verdict_icon}")
            except Exception as e:
                print(f"  └── 🛑 [CRITICAL CORE FAULT] Parsing error on {asset}: {e}")
        print("==========================================================================")

if __name__ == "__main__":
    validator = GlobalStructureExitValidator()
    validator.run_global_verification()
