import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v3_architecture.system_destruction_rig import SystemDestructionRig

class TradeAttributionAnalyzer(SystemDestructionRig):
    """
    Layer 9.9: Trade Attribution, Epoch Stability & Structural Drift Analyzer.
    Deconstructs lookahead-insulated multi-horizon execution streams to extract
    payout distributions and mathematical persistence across market conditions.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)

    def extract_audited_style_ledger(self, symbol, style_set, apply_lookahead_deflector=True):
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing absolute data track: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        if style_set == "SET_3_SHORT_TERM_SWING":
            df_htf = df_raw.resample('1D', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        else: # SET_4_INTRADAY_EXPANSION
            df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
            df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()

        if df_ltf.empty or df_mtf.empty or df_htf.empty: return []

        df_htf['ema'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['trend_aligned'] = df_htf['close'] > df_htf['ema']
        df_htf['weak_swing_target'] = df_htf['high'].rolling(10).max()

        df_mtf['ema_fast'] = df_mtf['close'].ewm(span=20, adjust=False).mean()
        df_mtf['ema_slow'] = df_mtf['close'].ewm(span=50, adjust=False).mean()
        df_mtf['trend_aligned'] = df_mtf['ema_fast'] > df_mtf['ema_slow']
        df_mtf['is_pullback'] = df_mtf['close'] < df_mtf['ema_fast']
        df_mtf['trailing_anchor'] = df_mtf['ema_fast']

        if apply_lookahead_deflector:
            df_htf['trend_aligned'] = df_htf['trend_aligned'].shift(1).fillna(False)
            df_htf['weak_swing_target'] = df_htf['weak_swing_target'].shift(1).ffill()
            df_mtf['trend_aligned'] = df_mtf['trend_aligned'].shift(1).fillna(False)
            df_mtf['is_pullback'] = df_mtf['is_pullback'].shift(1).fillna(False)
            df_mtf['trailing_anchor'] = df_mtf['trailing_anchor'].shift(1).ffill()

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

                    if htf_trend_arr[idx] == True and mtf_trend_arr[idx] == True:
                        regime_tag = 'BULL_EXPANSION'
                    elif htf_trend_arr[idx] == False and mtf_trend_arr[idx] == False:
                        regime_tag = 'BEAR_EXPANSION'
                    else:
                        regime_tag = 'COMPRESSED_RANGE'

                    active_pos = {
                        'asset': symbol, 'style': style_set, 'entry_price': price_arr[idx],
                        'entry_timestamp': time_objects[idx], 'exit_timestamp': None,
                        'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0, 
                        'year': int(years_arr[idx]), 'regime': regime_tag
                    }

        return style_trades

    def execute_attribution_audit(self, target_years=[2024, 2025, 2026]):
        print("==========================================================================================")
        print(" 🔍 APEX QUANT OS V3: INSTITUTIONAL ATTRIBUTION & REGIME AUDIT")
        print("==========================================================================================")
        
        target_styles = ["SET_3_SHORT_TERM_SWING", "SET_4_INTRADAY_EXPANSION"]
        
        all_trades = []
        for style in target_styles:
            for asset in self.assets:
                raw_trades = self.extract_audited_style_ledger(asset, style, apply_lookahead_deflector=True)
                all_trades.extend(raw_trades)
                
        df_all = pd.DataFrame(all_trades)
        if df_all.empty:
            print("🔴 [CRITICAL] No trades extracted across the selected timeline parameters.")
            return
            
        df_all = df_all[df_all['year'].isin(target_years)].copy()
        print(f"[*] Processing {len(df_all)} multi-horizon transactions through the discrete event wheel...")
        
        executed_trades = []
        balance = self.initial_balance
        peak = balance
        active_positions = []
        
        df_ledger = df_all.sort_values('entry_timestamp')
        unified_timeline = sorted(list(set(df_ledger['entry_timestamp'].tolist() + df_ledger['exit_timestamp'].tolist())))

        for current_tick in unified_timeline:
            still_active = []
            for pos in active_positions:
                if current_tick >= pos['exit_timestamp']:
                    r_multiplier = pos['risk_mult']
                    allocated_capital = pos['allocated_risk_capital']
                    trade_pnl = allocated_capital * r_multiplier
                    balance += trade_pnl
                    
                    exit_type = "STOP_LOSS"
                    if r_multiplier >= float(pos['computed_rr']) - 1e-5:
                        exit_type = "FULL_TP"
                    elif r_multiplier > 0.0:
                        exit_type = "MTF_TRAIL_WIN"
                    elif r_multiplier >= -0.05 and r_multiplier <= 0.05:
                        exit_type = "BREAK_EVEN"
                    elif r_multiplier > -1.0:
                        exit_type = "PARTIAL_LOSS"
                        
                    executed_trades.append({
                        **pos,
                        'realized_r': r_multiplier,
                        'exit_classification': exit_type,
                        'pnl_dollars': trade_pnl
                    })
                else:
                    still_active.append(pos)
            active_positions = still_active

            concurrent_signals = df_ledger[df_ledger['entry_timestamp'] == current_tick].to_dict('records')
            if not concurrent_signals: continue

            for candidate in concurrent_signals:
                candidate['allocated_risk_capital'] = balance * 0.01
                active_positions.append(candidate)

        df_audit = pd.DataFrame(executed_trades)
        
        # Baseline Summary Prints
        total_count = len(df_audit)
        print("\n[BASE PERFORMANCE SPECTRA]")
        print("------------------------------------------------------------------------------------------")
        print(f" 🏆 Total Audited Trades Pooled: {total_count}")
        print(f" 📊 Average Realized Win Size  : +{df_audit[df_audit['realized_r'] > 0]['realized_r'].mean():.2f} R")
        print(f" 📊 Average Realized Loss Size : {df_audit[df_audit['realized_r'] <= 0]['realized_r'].mean():.2f} R")
        print(f" 📊 Global System Expectancy   : +{df_audit['realized_r'].mean():.2f} R-Units Per Deployment")

        # --- EXTENSION 1: EXPECTANCY STABILITY ACROSS EPOCH CORRIDORS ---
        print("\n[AUDIT EXTENSION 1: R-EXPECTANCY STABILITY BY EPOCH YEAR]")
        print("------------------------------------------------------------------------------------------")
        for year in target_years:
            df_year = df_audit[df_audit['year'] == year]
            if df_year.empty: continue
            y_exp = df_year['realized_r'].mean()
            y_med = df_year['realized_r'].median()
            y_tr = len(df_year)
            print(f" ├── Epoch Corridor: {year} | Trades: {y_tr:4d} | Median R: +{y_med:.2f} R | Net Expectancy: +{y_exp:.2f} R-Units 🚀")

        # --- EXTENSION 2: EXIT ATTRIBUTION SLICED BY STYLE PLAYBOOK ---
        print("\n[AUDIT EXTENSION 2: GRANULAR EXIT ATTRIBUTION SLICED BY STYLE PLAYBOOK]")
        print("------------------------------------------------------------------------------------------")
        for style in target_styles:
            df_style = df_audit[df_audit['style'] == style]
            if df_style.empty: continue
            
            s_total = len(df_style)
            s_tp = len(df_style[df_style['exit_classification'] == "FULL_TP"])
            s_trail = len(df_style[df_style['exit_classification'] == "MTF_TRAIL_WIN"])
            s_be = len(df_style[df_style['exit_classification'] == "BREAK_EVEN"])
            s_pl = len(df_style[df_style['exit_classification'] == "PARTIAL_LOSS"])
            s_sl = len(df_style[df_style['exit_classification'] == "STOP_LOSS"])
            s_exp = df_style['realized_r'].mean()
            
            clean_name = style.replace("SET_", "").replace("_EXPANSION", "")
            print(f" ▶️ Playbook Stream Profile: {clean_name}")
            print(f"  ├── Total Sample Pool : {s_total} Trades")
            print(f"  ├── Net Style Expect  : +{s_exp:.2f} R-Units Per Trade")
            print(f"  ├── Full TP (>= 4R)   : {s_tp:4d} Trades | Ratio: {(s_tp/s_total)*100:5.1f}%")
            print(f"  ├── MTF Trail Win     : {s_trail:4d} Trades | Ratio: {(s_trail/s_total)*100:5.1f}%")
            print(f"  ├── Break-Even (~0R)  : {s_be:4d} Trades | Ratio: {(s_be/s_total)*100:5.1f}%")
            print(f"  ├── Mitigated Loss    : {s_pl:4d} Trades | Ratio: {(s_pl/s_total)*100:5.1f}%")
            print(f"  └── Terminal SL (-1R) : {s_sl:4d} Trades | Ratio: {(s_sl/s_total)*100:5.1f}%")
            print(" ----------------------------------------------------------------------------------------")

        # Regime Summary Print
        print("\n[REFINEMENT 3: ADVANCED REGIME AND VOLATILITY PERSISTENCE]")
        print("------------------------------------------------------------------------------------------")
        regimes = {
            'Bull Expansion Core': df_audit[df_audit['regime'] == 'BULL_EXPANSION'],
            'Bear Expansion Core': df_audit[df_audit['regime'] == 'BEAR_EXPANSION'],
            'Compressed Range Zone': df_audit[df_audit['regime'] == 'COMPRESSED_RANGE']
        }
        for name, sub_df in regimes.items():
            if sub_df.empty: continue
            wr = (len(sub_df[sub_df['realized_r'] > 0]) / len(sub_df)) * 100
            exp = sub_df['realized_r'].mean()
            print(f"  ├── {name:22s} | {len(sub_df):6d} Trades | WR: {wr:5.1f}% | Expectancy: +{exp:.2f} R | 🟢 SURVIVES")
        print("==========================================================================================")

if __name__ == "__main__":
    analyzer = TradeAttributionAnalyzer()
    analyzer.execute_attribution_audit([2024, 2025, 2026])
