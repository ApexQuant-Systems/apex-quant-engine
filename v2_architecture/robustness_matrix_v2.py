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

class MasterProfileRobustnessMatrix:
    """
    Layer 6: Industrial Robustness Matrix Framework.
    Supports Multi-Asset, Multi-Year Walk-Forward, and multi-layer 
    Trading Profiles (Investment, Position, Swing, Intraday).
    """
    def __init__(self, target_rr=4.0):
        self.target_rr = target_rr
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_profile_matrices(self, df_1m, profile_name):
        """
        Dynamically resamples raw 1m data blocks to fit specific target trading profiles.
        """
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        if profile_name == 'INVESTMENT':
            htf = df_1m.resample('1ME', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            mtf = df_1m.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            ltf = df_1m.resample('1d', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        elif profile_name == 'POSITION':
            htf = df_1m.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            mtf = df_1m.resample('1d', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            ltf = df_1m.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        elif profile_name == 'SWING':
            htf = df_1m.resample('1d', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            mtf = df_1m.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            ltf = df_1m.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        else: # INTRADAY default profile setup
            htf = df_1m.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            mtf = df_1m.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            ltf = df_1m.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            
        for df in [htf, mtf, ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)
            
        return htf, mtf, ltf

    def evaluate_matrix(self, symbol, profile_name):
        # Locate the clean raw file path directly
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        df_htf, df_mtf, df_ltf = self.generate_profile_matrices(df_raw, profile_name)
        
        # --- VECTORIZED METRIC CALCULATION CORE ---
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['roll_high'] = df_htf['high'].rolling(window=14).max()
        df_htf['roll_low'] = df_htf['low'].rolling(window=14).min()
        df_htf['vol_ratio'] = (df_htf['roll_high'] - df_htf['roll_low']) / (df_htf['atr'] + 1e-8)
        
        df_htf['regime'] = "CHOPPY_RANGE"
        df_htf.loc[(df_htf['vol_ratio'] >= 3.0) & (df_htf['close'] > df_htf['ema_20']) & (df_htf['ema_20'] > df_htf['ema_50']), 'regime'] = "TRENDING_BULL"

        df_mtf['eq_high'] = df_mtf['high'].rolling(30).max()
        df_mtf['eq_low'] = df_mtf['low'].rolling(30).min()
        df_mtf['equilibrium'] = (df_mtf['eq_high'] + df_mtf['eq_low']) / 2.0
        
        df_mtf['has_bull_fvg'] = False
        h_mtf, l_mtf = df_mtf['high'].to_numpy(), df_mtf['low'].to_numpy()
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = h_mtf[:-2] < l_mtf[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)

        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_htf.size > 5 and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        # Pointer Maps
        ts_ltf = df_ltf['timestamp'].to_numpy()
        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), ts_ltf, side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), ts_ltf, side='right') - 1, 0, len(df_mtf) - 1)

        price_arr = df_ltf['close'].to_numpy()
        high_arr = df_ltf['high'].to_numpy()
        low_arr = df_ltf['low'].to_numpy()
        
        regimes_htf = df_htf['regime'].to_numpy()[idx_htf]
        eq_mtf = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        bull_fvg_mtf = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        ltf_sh = df_ltf['last_visible_sh'].to_numpy()
        
        # --- ZERO BUG PIN: Extract year parameters natively from pandas datetime array ---
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        trades_by_year = {2024: [], 2025: [], 2026: []}
        balance = 10000.0
        active_position = None
        
        for idx in range(100, len(df_ltf)):
            current_year = years_arr[idx]
            if current_year not in trades_by_year:
                continue
                
            current_price = price_arr[idx]
            current_high = high_arr[idx]
            current_low = low_arr[idx]

            if active_position:
                pos = active_position
                if current_low <= pos['sl']:
                    loss_pnl = -pos['risk_capital']
                    balance += loss_pnl
                    trades_by_year[pos['year_opened']].append({'status': 'LOSS', 'pnl': loss_pnl})
                    active_position = None
                elif current_high >= pos['tp']:
                    win_pnl = pos['risk_capital'] * self.target_rr
                    balance += win_pnl
                    trades_by_year[pos['year_opened']].append({'status': 'WIN', 'pnl': win_pnl})
                    active_position = None
                continue

            if regimes_htf[idx] == "TRENDING_BULL" and current_price < eq_mtf[idx]:
                if bull_fvg_mtf[idx] and not np.isnan(ltf_sh[idx]) and current_price > ltf_sh[idx]:
                    sl_price = current_low * 0.995
                    size = self.risk_engine.calculate_position_size(balance, current_price, sl_price, self.instrument_config)
                    if size > 0:
                        active_position = {
                            'sl': sl_price, 'risk_capital': size * (current_price - sl_price),
                            'tp': current_price + ((current_price - sl_price) * self.target_rr),
                            'year_opened': current_year
                        }

        report = {}
        for yr, journal in trades_by_year.items():
            if len(journal) == 0:
                report[yr] = {'trades': 0, 'pf': '0.00', 'pnl': '$0.00'}
                continue
            df_j = pd.DataFrame(journal)
            wins = len(df_j[df_j['status'] == 'WIN'])
            total_won = df_j[df_j['pnl'] > 0]['pnl'].sum()
            total_lost = abs(df_j[df_j['pnl'] < 0]['pnl'].sum())
            pf = total_won / total_lost if total_lost > 0 else total_won
            net_pnl = df_j['pnl'].sum()
            
            report[yr] = {'trades': len(df_j), 'pf': f"{pf:.2f}", 'pnl': f"${net_pnl:+,.2f}"}
        return report

if __name__ == "__main__":
    matrix_engine = MasterProfileRobustnessMatrix()
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    profiles = ["INVESTMENT", "POSITION", "SWING", "INTRADAY"]
    
    print("\n==========================================================================")
    print("         👑 APEX QUANT OS v2: GLOBAL TARGET TOURNAMENT MATRIX")
    print("==========================================================================")
    print(f" {'ASSET':7s} | {'PROFILE':10s} | {'YEAR':4s} | {'TRADES':6s} | {'PROFIT FACTOR':13s} | {'NET PNL':11s} |")
    print("--------------------------------------------------------------------------")
    
    for asset in assets:
        for profile in profiles:
            try:
                report = matrix_engine.evaluate_matrix(asset, profile)
                for year, metrics in report.items():
                    if metrics['trades'] > 0: # Only report active performance nodes
                        print(f" {asset:7s} | {profile:10s} | {str(year):4s} | {metrics['trades']:6d} | {metrics['pf']:13s} | {metrics['pnl']:11s} |")
            except Exception as e:
                continue
    print("==========================================================================")
