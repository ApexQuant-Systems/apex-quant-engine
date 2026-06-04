import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class BTCRegimeAttributionEngine:
    """
    Layer 6.9.8: Production Regime Attribution Diagnostics Engine.
    Dissects the historical trade log of the Structure Liquidity model,
    categorizing performance into explicit volatility and trend regimes.
    """
    def __init__(self, symbol="BTCUSDT", initial_balance=10000.0):
        self.symbol = symbol
        self.initial_balance = initial_balance

    def extract_attributed_trades(self):
        raw_path = Path(f"./data/raw/{self.symbol}/{self.symbol}_1m_archive.csv")
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        # Build Standard Intraday Resampling Track
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # 4H Volatility Regime Metrics
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr_htf = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr_htf = np.insert(tr_htf, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr_htf).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        # 1H Micro-Structure Metrics
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        # 15M Entry Matrix
        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        # Map Pointer Channels
        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        # Bind Environmental States directly onto the LTF execution frame
        df_ltf['macro_vol_ratio'] = df_htf['vol_ratio'].to_numpy()[idx_htf]
        df_ltf['macro_close'] = df_htf['close'].to_numpy()[idx_htf]
        df_ltf['macro_ema_20'] = df_htf['ema_20'].to_numpy()[idx_htf]
        df_ltf['macro_ema_50'] = df_htf['ema_50'].to_numpy()[idx_htf]
        
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]

        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()
        eq_mtf = df_ltf['eq_mtf'].to_numpy()
        
        v_ratios = df_ltf['macro_vol_ratio'].to_numpy()
        m_closes = df_ltf['macro_close'].to_numpy()
        ema_20s = df_ltf['macro_ema_20'].to_numpy()
        ema_50s = df_ltf['macro_ema_50'].to_numpy()

        trade_log = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    active_pos['status'] = 'LOSS'
                    active_pos['pnl'] = -1.0
                    trade_log.append(active_pos)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    active_pos['status'] = 'WIN'
                    active_pos['pnl'] = active_pos['computed_rr']
                    trade_log.append(active_pos)
                    active_pos = None
                continue

            if price_arr[idx] < eq_mtf[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                sl = low_arr[idx] * 0.995
                risk_distance = price_arr[idx] - sl
                if risk_distance <= 0:
                    continue
                tp = liq_arr[idx]
                computed_rr = (tp - price_arr[idx]) / risk_distance
                if computed_rr < 1.5:
                    continue

                vol = v_ratios[idx]
                c_price = m_closes[idx]
                e20 = ema_20s[idx]
                e50 = ema_50s[idx]

                if vol >= 3.0 and c_price > e20 and e20 > e50:
                    regime_tag = 'BULL_EXPANSION'
                elif vol >= 3.0 and c_price < e20 and e20 < e50:
                    regime_tag = 'BEAR_EXPANSION'
                else:
                    regime_tag = 'COMPRESSED_RANGE'

                # PINNED: Restored missing 'sl' and 'tp' dictionary target anchors
                active_pos = {
                    'sl': sl,
                    'tp': tp,
                    'regime': regime_tag,
                    'computed_rr': computed_rr,
                    'status': None,
                    'pnl': 0.0
                }

        return trade_log

    def run_attribution_analysis(self):
        print("\n==========================================================================")
        print(f" GENERATING PRODUCTION REGIME ATTRIBUTION REPORT FOR: {self.symbol}")
        print("==========================================================================")
        
        trades = self.extract_attributed_trades()
        if not trades:
            print("[⚠️ NOTICE] Attribution engine returned 0 trades under research criteria.")
            return

        df = pd.DataFrame(trades)
        
        print(f" {'REGIME TYPE':18s} | {'TRADES':6s} | {'WIN RATE':8s} | {'PROFIT FACTOR':13s} | {'EXPECTANCY':10s} |")
        print("--------------------------------------------------------------------------")
        
        for regime in ['BULL_EXPANSION', 'BEAR_EXPANSION', 'COMPRESSED_RANGE']:
            sub = df[df['regime'] == regime]
            if sub.empty:
                print(f" {regime:18s} | {0:6d} | {'0.0%':8s} | {'0.00':13s} | {'0.00R':10s} |")
                continue
                
            total_trades = len(sub)
            wins = len(sub[sub['status'] == 'WIN'])
            wr = (wins / total_trades) * 100
            
            total_won = sub[sub['pnl'] > 0]['pnl'].sum()
            total_lost = abs(sub[sub['pnl'] < 0]['pnl'].sum())
            pf = total_won / total_lost if total_lost > 0 else total_won
            expectancy = sub['pnl'].mean()
            
            print(f" {regime:18s} | {total_trades:6d} | {wr:5.1f}% | {pf:13.2f} | {expectancy:+8.2f}R |")
            print("--------------------------------------------------------------------------")
        print("==========================================================================")

if __name__ == "__main__":
    engine = BTCRegimeAttributionEngine()
    engine.run_attribution_analysis()
