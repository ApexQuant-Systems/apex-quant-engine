import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v2_architecture.portfolio_event_engine import PortfolioEventEngine

class HierarchicalDecisionEngine(PortfolioEventEngine):
    """
    Apex Quant OS v3: Isolated Multi-Horizon Hierarchical Style Matrix.
    Processes four completely isolated strategy sets using pure HTF Bias,
    MTF Pullback/Trailing, and LTF Entry rules with strict >= 4.0R gates.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)
        self.cartridge_confidence = {"BTCUSDT": 95, "SOLUSDT": 85, "ETHUSDT": 70}

    def compute_pure_style_ledger(self, symbol, style_set):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing absolute data track: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        if style_set == "SET_1_LONG_TERM_INVESTING":
            df_htf = df_raw.resample('1ME', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        elif style_set == "SET_2_INTERMEDIATE_SWING":
            df_htf = df_raw.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        elif style_set == "SET_3_SHORT_TERM_SWING":
            df_htf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        else: # SET_4_INTRADAY_EXPANSION
            df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()

        if df_ltf.empty or df_mtf.empty or df_htf.empty: 
            return []

        # --- HTF LAYER: BIAS FILTERS ---
        df_htf['ema'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['trend_aligned'] = df_htf['close'] > df_htf['ema']
        df_htf['weak_swing_target'] = df_htf['high'].rolling(10).max()

        # --- PATCHED MTF LAYER: DECOUPLED CROSSOVER STRUCTURE ---
        df_mtf['ema_fast'] = df_mtf['close'].ewm(span=20, adjust=False).mean()
        df_mtf['ema_slow'] = df_mtf['close'].ewm(span=50, adjust=False).mean()
        # Structural trend is defined by the directional alignment of the moving average stack
        df_mtf['trend_aligned'] = df_mtf['ema_fast'] > df_mtf['ema_slow']
        # The pullback condition checks if the current close is at a discount below the fast baseline
        df_mtf['is_pullback'] = df_mtf['close'] < df_mtf['ema_fast']
        df_mtf['trailing_anchor'] = df_mtf['ema_fast']

        # --- LTF LAYER: PRECISION ENTRY ZONES ---
        df_ltf['ema'] = df_ltf['close'].ewm(span=20, adjust=False).mean()
        df_ltf['trend_aligned'] = df_ltf['close'] > df_ltf['ema']
        df_ltf['strong_zone_sl'] = df_ltf['low'].rolling(5).min()

        idx_htf = np.clip(np.searchsorted(df_htf['datetime'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['datetime'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['htf_trend'] = df_htf['trend_aligned'].to_numpy()[idx_htf]
        df_ltf['htf_target'] = df_htf['weak_swing_target'].to_numpy()[idx_htf]
        df_ltf['mtf_trend'] = df_mtf['trend_aligned'].to_numpy()[idx_mtf]
        df_ltf['mtf_pullback'] = df_mtf['is_pullback'].to_numpy()[idx_mtf]
        df_ltf['mtf_trail_stop'] = df_mtf['trailing_anchor'].to_numpy()[idx_mtf]

        price_arr, low_arr, high_arr = df_ltf['close'].to_numpy(), df_ltf['low'].to_numpy(), df_ltf['high'].to_numpy()
        htf_trend_arr, htf_target_arr = df_ltf['htf_trend'].to_numpy(), df_ltf['htf_target'].to_numpy()
        mtf_trend_arr, mtf_pullback_arr, mtf_trail_arr = df_ltf['mtf_trend'].to_numpy(), df_ltf['mtf_pullback'].to_numpy(), df_ltf['mtf_trail_stop'].to_numpy()
        ltf_trend_arr, ltf_sl_arr = df_ltf['trend_aligned'].to_numpy(), df_ltf['strong_zone_sl'].to_numpy()
        
        time_objects = df_ltf['datetime'].tolist()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        style_trades = []
        active_pos = None

        for idx in range(50, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    active_pos['exit_timestamp'] = time_objects[idx]
                    active_pos['risk_mult'] = -1.0
                    style_trades.append(active_pos)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    active_pos['exit_timestamp'] = time_objects[idx]
                    active_pos['risk_mult'] = float(active_pos['computed_rr'])
                    style_trades.append(active_pos)
                    active_pos = None
                elif low_arr[idx] <= mtf_trail_arr[idx]:
                    active_pos['exit_timestamp'] = time_objects[idx]
                    risk_dist = abs(active_pos['entry_price'] - active_pos['sl'])
                    trail_pnl = (mtf_trail_arr[idx] - active_pos['entry_price']) / (risk_dist + 1e-8)
                    active_pos['risk_mult'] = max(-1.0, float(trail_pnl))
                    style_trades.append(active_pos)
                    active_pos = None
                continue

            if htf_trend_arr[idx] == True and mtf_trend_arr[idx] == True and ltf_trend_arr[idx] == True:
                if mtf_pullback_arr[idx] == True:
                    sl = ltf_sl_arr[idx]
                    tp = htf_target_arr[idx]
                    
                    risk_dist = abs(price_arr[idx] - sl)
                    if risk_dist <= 0: continue
                    
                    computed_rr = (tp - price_arr[idx]) / risk_dist

                    if computed_rr < 4.0 or np.isnan(computed_rr): 
                        continue

                    active_pos = {
                        'asset': symbol, 'style': style_set, 'entry_price': price_arr[idx],
                        'entry_timestamp': time_objects[idx], 'exit_timestamp': None,
                        'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0, 'year': int(years_arr[idx])
                    }

        return style_trades
