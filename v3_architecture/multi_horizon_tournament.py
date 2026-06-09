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

class MultiHorizonTournament(PortfolioEventEngine):
    """
    Apex Quant OS v3: Multi-Horizon Business Tournament Core.
    Establishes 4 distinct, un-mixed timeframe sets running symmetrical 
    Long (Bull) and Short (Bear) playbooks under lookahead insulation constraints.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)
        self.style_sets = [
            "SET_1_MACRO_INVESTING",
            "SET_2_MEDIUM_SWING",
            "SET_3_SHORT_POSITION",
            "SET_4_INTRADAY_EXPANSION"
        ]

    def generate_pure_horizon_ledger(self, symbol, style_set):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing absolute data track: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        # Isolate higher-timeframe boundaries into clean corporate modules
        if style_set == "SET_1_MACRO_INVESTING":
            df_htf = df_raw.resample('1ME', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            roll_htf, roll_ltf = 3, 3 # Adaptive windows to prevent lookback starvation on macro bars
        elif style_set == "SET_2_MEDIUM_SWING":
            df_htf = df_raw.resample('1W', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            roll_htf, roll_ltf = 5, 4
        elif style_set == "SET_3_SHORT_POSITION":
            df_htf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            roll_htf, roll_ltf = 10, 5
        else: # SET_4_INTRADAY_EXPANSION
            df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            roll_htf, roll_ltf = 10, 5

        if df_ltf.empty or df_mtf.empty or df_htf.empty: return []

        # --- HTF BIAS LAYER (LONG & SHORT SLOTS) ---
        df_htf['ema'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['bull_bias'] = df_htf['close'] > df_htf['ema']
        df_htf['bear_bias'] = df_htf['close'] < df_htf['ema']
        
        # Rolling boundaries map weak structural targets dynamically
        df_htf['weak_high_target'] = df_htf['high'].rolling(roll_htf).max()
        df_htf['weak_low_target'] = df_htf['low'].rolling(roll_htf).min()

        # --- MTF SETUP LAYER (EMA CROSSOVER TRACKS) ---
        df_mtf['ema_fast'] = df_mtf['close'].ewm(span=20, adjust=False).mean()
        df_mtf['ema_slow'] = df_mtf['close'].ewm(span=50, adjust=False).mean()
        df_mtf['bull_trend'] = df_mtf['ema_fast'] > df_mtf['ema_slow']
        df_mtf['bear_trend'] = df_mtf['ema_fast'] < df_mtf['ema_slow']
        
        df_mtf['bull_pullback'] = df_mtf['close'] < df_mtf['ema_fast']
        df_mtf['bear_pullback'] = df_mtf['close'] > df_mtf['ema_fast']
        df_mtf['trailing_anchor'] = df_mtf['ema_fast']

        # --- LAUNCH INSTANT 1-BAR LOOKAHEAD DEFLECTOR SUITE ---
        df_htf['bull_bias'] = df_htf['bull_bias'].shift(1).fillna(False)
        df_htf['bear_bias'] = df_htf['bear_bias'].shift(1).fillna(False)
        df_htf['weak_high_target'] = df_htf['weak_high_target'].shift(1).ffill()
        df_htf['weak_low_target'] = df_htf['weak_low_target'].shift(1).ffill()
        
        df_mtf['bull_trend'] = df_mtf['bull_trend'].shift(1).fillna(False)
        df_mtf['bear_trend'] = df_mtf['bear_trend'].shift(1).fillna(False)
        df_mtf['bull_pullback'] = df_mtf['bull_pullback'].shift(1).fillna(False)
        df_mtf['bear_pullback'] = df_mtf['bear_pullback'].shift(1).fillna(False)
        df_mtf['trailing_anchor'] = df_mtf['trailing_anchor'].shift(1).ffill()

        # --- LTF ENTRY LAYER ---
        df_ltf['ema'] = df_ltf['close'].ewm(span=20, adjust=False).mean()
        df_ltf['bull_trigger'] = df_ltf['close'] > df_ltf['ema']
        df_ltf['bear_trigger'] = df_ltf['close'] < df_ltf['ema']
        
        df_ltf['strong_support_zone'] = df_ltf['low'].rolling(roll_ltf).min()
        df_ltf['strong_resistance_zone'] = df_ltf['high'].rolling(roll_ltf).max()

        # Sync timeframe data layers securely via index search mapping
        idx_htf = np.clip(np.searchsorted(df_htf['datetime'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['datetime'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['htf_bull_bias'] = df_htf['bull_bias'].to_numpy()[idx_htf]
        df_ltf['htf_bear_bias'] = df_htf['bear_bias'].to_numpy()[idx_htf]
        df_ltf['htf_high_tp'] = df_htf['weak_high_target'].to_numpy()[idx_htf]
        df_ltf['htf_low_tp'] = df_htf['weak_low_target'].to_numpy()[idx_htf]
        
        df_ltf['mtf_bull_trend'] = df_mtf['bull_trend'].to_numpy()[idx_mtf]
        df_ltf['mtf_bear_trend'] = df_mtf['bear_trend'].to_numpy()[idx_mtf]
        df_ltf['mtf_bull_pull'] = df_mtf['bull_pullback'].to_numpy()[idx_mtf]
        df_ltf['mtf_bear_pull'] = df_mtf['bear_pullback'].to_numpy()[idx_mtf]
        df_ltf['mtf_trail'] = df_mtf['trailing_anchor'].to_numpy()[idx_mtf]

        # Extract underlying memory arrays for optimized iteration loops
        p_arr, l_arr, h_arr = df_ltf['close'].to_numpy(), df_ltf['low'].to_numpy(), df_ltf['high'].to_numpy()
        h_bull_bias, h_bear_bias, h_tp_high, h_tp_low = df_ltf['htf_bull_bias'].to_numpy(), df_ltf['htf_bear_bias'].to_numpy(), df_ltf['htf_high_tp'].to_numpy(), df_ltf['htf_low_tp'].to_numpy()
        m_bull_trend, m_bear_trend, m_bull_pull, m_bear_pull, m_trail = df_ltf['mtf_bull_trend'].to_numpy(), df_ltf['mtf_bear_trend'].to_numpy(), df_ltf['mtf_bull_pull'].to_numpy(), df_ltf['mtf_bear_pull'].to_numpy(), df_ltf['mtf_trail'].to_numpy()
        l_bull_trig, l_bear_trig, l_support, l_resist = df_ltf['bull_trigger'].to_numpy(), df_ltf['bear_trigger'].to_numpy(), df_ltf['strong_support_zone'].to_numpy(), df_ltf['strong_resistance_zone'].to_numpy()
        
        time_objects = df_ltf['datetime'].tolist()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        trades = []
        active_pos = None

        for idx in range(50, len(df_ltf)):
            if active_pos:
                if active_pos['direction'] == 'LONG':
                    if l_arr[idx] <= active_pos['sl']:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        active_pos['risk_mult'] = -1.0
                        trades.append(active_pos); active_pos = None
                    elif h_arr[idx] >= active_pos['tp']:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        active_pos['risk_mult'] = float(active_pos['computed_rr'])
                        trades.append(active_pos); active_pos = None
                    elif l_arr[idx] <= m_trail[idx]:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        r_dist = abs(active_pos['entry_price'] - active_pos['sl'])
                        trail_pnl = (m_trail[idx] - active_pos['entry_price']) / (r_dist + 1e-8)
                        active_pos['risk_mult'] = max(-1.0, float(trail_pnl))
                        trades.append(active_pos); active_pos = None
                else: # SHORT position management logic
                    if h_arr[idx] >= active_pos['sl']:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        active_pos['risk_mult'] = -1.0
                        trades.append(active_pos); active_pos = None
                    elif l_arr[idx] <= active_pos['tp']:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        active_pos['risk_mult'] = float(active_pos['computed_rr'])
                        trades.append(active_pos); active_pos = None
                    elif h_arr[idx] >= m_trail[idx]:
                        active_pos['exit_timestamp'] = time_objects[idx]
                        r_dist = abs(active_pos['sl'] - active_pos['entry_price'])
                        trail_pnl = (active_pos['entry_price'] - m_trail[idx]) / (r_dist + 1e-8)
                        active_pos['risk_mult'] = max(-1.0, float(trail_pnl))
                        trades.append(active_pos); active_pos = None
                continue

            # 1. PURE STYLE LONG ARENA (BULL EXPANSION SECTOR)
            if h_bull_bias[idx] and m_bull_trend[idx] and l_bull_trig[idx] and m_bull_pull[idx]:
                sl = l_support[idx]
                tp = h_tp_high[idx]
                risk_dist = abs(p_arr[idx] - sl)
                if risk_dist <= 0: continue
                computed_rr = (tp - p_arr[idx]) / risk_dist
                
                if computed_rr >= 4.0 and not np.isnan(computed_rr):
                    active_pos = {
                        'asset': symbol, 'style': style_set, 'direction': 'LONG', 'regime': 'BULL_EXPANSION',
                        'entry_price': p_arr[idx], 'entry_timestamp': time_objects[idx], 'exit_timestamp': None,
                        'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0, 'year': int(years_arr[idx])
                    }
                    continue

            # 2. PURE STYLE SHORT ARENA (BEAR EXPANSION SECTOR)
            if h_bear_bias[idx] and m_bear_trend[idx] and l_bear_trig[idx] and m_bear_pull[idx]:
                sl = l_resist[idx]
                tp = h_tp_low[idx]
                risk_dist = abs(sl - p_arr[idx])
                if risk_dist <= 0: continue
                computed_rr = (p_arr[idx] - tp) / risk_dist
                
                if computed_rr >= 4.0 and not np.isnan(computed_rr):
                    active_pos = {
                        'asset': symbol, 'style': style_set, 'direction': 'SHORT', 'regime': 'BEAR_EXPANSION',
                        'entry_price': p_arr[idx], 'entry_timestamp': time_objects[idx], 'exit_timestamp': None,
                        'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0, 'year': int(years_arr[idx])
                    }

        return trades

    def execute_corporate_tournament(self, epochs=[2024, 2025, 2026]):
        print("==========================================================================================")
        print(" 🏛️ APEX QUANT OS V3: FOUR HORIZONS MULTI-REGIME TOURNAMENT CORE")
        print("==========================================================================================")
        
        scorecard_rows = []
        
        for style in self.style_sets:
            print(f"\n[*] Auditing Standalone Corporate Horizon: {style}")
            print(" ----------------------------------------------------------------------------------------")
            
            style_ledger = []
            for asset in self.assets:
                try:
                    asset_style_trades = self.generate_pure_horizon_ledger(asset, style)
                    style_ledger.extend(asset_style_trades)
                except Exception as e:
                    print(f"  └── [WARNING] Initialisation breakdown on {asset} under {style}: {e}")
                    
            df_style = pd.DataFrame(style_ledger)
            
            # If a business horizon generates zero multi-year trades, log it as out of business gracefully
            if df_style.empty or 'year' not in df_style.columns:
                print(f"  🔴 Corporate Domain Silenced: Zero viable alerts generated across entire epoch history.")
                scorecard_rows.append({
                    'Corporate Horizon': style.replace("SET_", ""), 'Total Trades': 0, 'WinRate %': 0.0,
                    'Global Expectancy': 0.0, 'Bull Expect': 0.0, 'Bear Expect': 0.0, 'Verdict': '🔴 SHELVED (NO ALPHA)'
                })
                continue

            # Process metrics for active horizons
            df_filtered = df_style[df_style['year'].isin(epochs)].copy()
            t_count = len(df_filtered)
            
            if t_count == 0:
                scorecard_rows.append({
                    'Corporate Horizon': style.replace("SET_", ""), 'Total Trades': 0, 'WinRate %': 0.0,
                    'Global Expectancy': 0.0, 'Bull Expect': 0.0, 'Bear Expect': 0.0, 'Verdict': '🔴 SHELVED (NO ALPHA)'
                })
                continue
                
            wr = (len(df_filtered[df_filtered['risk_mult'] > 0]) / t_count) * 100
            global_expectancy = df_filtered['risk_mult'].mean()
            
            # Symmetrical partition tracking
            df_bull = df_filtered[df_filtered['regime'] == 'BULL_EXPANSION']
            df_bear = df_filtered[df_filtered['regime'] == 'BEAR_EXPANSION']
            
            bull_exp = df_bull['risk_mult'].mean() if not df_bull.empty else 0.0
            bear_exp = df_bear['risk_mult'].mean() if not df_bear.empty else 0.0
            
            verdict = "🟢 PASSED REGIME GATE" if global_expectancy >= 0.05 else "🔴 ELIMINATED (SUB-HERD METRICS)"
            
            scorecard_rows.append({
                'Corporate Horizon': style.replace("SET_", ""),
                'Total Trades': t_count,
                'WinRate %': round(wr, 1),
                'Global Expectancy': round(global_expectancy, 2),
                'Bull Expect': round(bull_exp, 2),
                'Bear Expect': round(bear_exp, 2),
                'Verdict': verdict
            })
            
            print(f"  ├── Global Horizon Volume : {t_count} Total Trades across 3-Asset Registry")
            print(f"  ├── Symmetrical Balance  : Bull Pool Expect: +{bull_exp:.2f}R | Bear Pool Expect: +{bear_exp:.2f}R")
            print(f"  └── Ultimate Operational R Expectancy Value: +{global_expectancy:.2f} R-Units Per Trade -> {verdict}")

        df_leaderboard = pd.DataFrame(scorecard_rows)
        print("\n==========================================================================================")
        print(" 📊 THE FOUR HORIZON BUSINESS MATRIX LEADERBOARD (LOOKAHEAD-INSULATED)")
        print("==========================================================================================")
        print(df_leaderboard.to_string(index=False))
        print("==========================================================================================")

if __name__ == "__main__":
    tournament = MultiHorizonTournament()
    tournament.execute_corporate_tournament([2024, 2025, 2026])
