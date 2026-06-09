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

class LossClusterAnalyzer(PortfolioEventEngine):
    """
    Layer 9.6: Systemic Factor Drag & Loss Cluster Diagnostic Platform.
    Chronologically traces the portfolio core using native pd.Timestamp objects
    to log every firewall scale change, exposing hidden risk correlation loops.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)

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

        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = df_mtf['high'].shift(2) < df_mtf['low']
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        # Reconstruct standard matching sorted alignments
        df_htf['search_time'] = df_htf['datetime']
        df_mtf['search_time'] = df_mtf['datetime']
        
        idx_htf = np.clip(np.searchsorted(df_htf['search_time'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['search_time'].to_numpy(), df_ltf['datetime'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

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
        
        time_objects = df_ltf['datetime'].tolist()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        trades = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    active_pos['exit_timestamp'] = time_objects[idx]
                    active_pos['risk_mult'] = -1.0
                    trades.append(active_pos)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    active_pos['exit_timestamp'] = time_objects[idx]
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

                # Pinned to clear pd.Timestamp reference handles
                active_pos = {
                    'asset': symbol, 'entry_timestamp': time_objects[idx], 'exit_timestamp': None,
                    'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0,
                    'regime': regime_tag, 'year': int(years_arr[idx])
                }
        return trades

    def execute_diagnostic_audit(self, target_years):
        global_ledger = []
        for asset in self.assets:
            trades = self.extract_cartridge_trades(asset)
            global_ledger.extend(trades)
            
        global_ledger = sorted(global_ledger, key=lambda x: x['entry_timestamp'])
        
        balance = self.initial_balance
        peak = balance
        active_positions = []
        state_history = []

        # Create a native chronological sequence using true pd.Timestamp objects
        unified_timeline = sorted(list(set([t['entry_timestamp'] for t in global_ledger if t['year'] in target_years] + 
                                           [t['exit_timestamp'] for t in global_ledger if t['exit_timestamp'] is not None and t['year'] in target_years])))

        for current_tick in unified_timeline:
            still_active = []
            
            # 1. Process exits matching the current market tick
            for pos in active_positions:
                if current_tick >= pos['exit_timestamp']:
                    trade_pnl = pos['allocated_risk_capital'] * pos['risk_mult']
                    balance += trade_pnl
                    
                    state_history.append({
                        'datetime': current_tick.strftime('%Y-%m-%d %H:%M'),
                        'event_type': 'EXIT', 'asset': pos['asset'],
                        'status': 'WIN' if pos['risk_mult'] > 0 else 'LOSS',
                        'allocated_risk_pct': pos['risk_budget_pct'] * 100,
                        'net_pnl': trade_pnl, 'current_balance': balance,
                        'current_dd': ((peak - balance) / peak) * 100,
                        'firewall_scale': pos['firewall_scale_at_entry']
                    })
                else:
                    still_active.append(pos)
            active_positions = still_active

            if balance > peak: peak = balance
            current_dd = (peak - balance) / peak

            # 2. Process incoming alerts matching the current market tick
            concurrent_signals = [t for t in global_ledger if t['entry_timestamp'] == current_tick and t['year'] in target_years]
            if not concurrent_signals: continue

            current_heat = sum([p['risk_budget_pct'] for p in active_positions])
            available_heat = self.max_portfolio_heat - current_heat

            if current_dd >= 0.25: risk_scale = 0.0000
            elif current_dd >= 0.20: risk_scale = 0.0025
            elif current_dd >= 0.15: risk_scale = 0.0050
            elif current_dd >= 0.10: risk_scale = 0.0075
            else: risk_scale = 1.0000

            scored_candidates = []
            for sig in concurrent_signals:
                base_conf = self.cartridge_confidence.get(sig['asset'], 50)
                priority_score = base_conf * sig['computed_rr']
                scored_candidates.append({**sig, 'priority_score': priority_score})
            scored_candidates = sorted(scored_candidates, key=lambda x: x['priority_score'], reverse=True)

            for candidate in scored_candidates:
                if available_heat <= 0: break
                target_risk_slot = 0.01
                allocated_risk = target_risk_slot if available_heat >= target_risk_slot else available_heat

                final_risk_pct = allocated_risk * risk_scale
                if final_risk_pct <= 0: continue

                candidate['risk_budget_pct'] = final_risk_pct
                candidate['allocated_risk_capital'] = balance * final_risk_pct
                candidate['firewall_scale_at_entry'] = risk_scale
                
                active_positions.append(candidate)
                available_heat -= final_risk_pct
                
                state_history.append({
                    'datetime': current_tick.strftime('%Y-%m-%d %H:%M'),
                    'event_type': 'ENTRY', 'asset': candidate['asset'], 'status': 'PENDING',
                    'allocated_risk_pct': final_risk_pct * 100, 'net_pnl': 0.0,
                    'current_balance': balance, 'current_dd': current_dd * 100,
                    'firewall_scale': risk_scale
                })

        df_audit = pd.DataFrame(state_history)
        
        print("\n==========================================================================================")
        print(" 🔒 APEX QUANT OS CORE: UN-ALIASED CHRONOLOGICAL FACTOR LOSS CLUSTER AUDIT")
        print("==========================================================================================")
        print(f" Total Portfolio Operations Tracked : {len(df_audit)}")
        print(f" Final Operational Balance          : ${balance:,.2f}")
        print("------------------------------------------------------------------------------------------")
        
        # Isolate the precise timeline segments displaying major drawdown spikes
        print("\n[EXPOSING DYNAMIC PORTFOLIO LIFECYCLE TRANSITIONS]")
        print(f" {'DATETIME':16s} | {'EVENT':5s} | {'ASSET':8s} | {'STATUS':4s} | {'RISK ALLOC %':12s} | {'NET PNL':10s} | {'FIREWALL':8s} |")
        print("------------------------------------------------------------------------------------------")
        
        # Sort by drawdown peaks to view the worst cluster impact zones
        worst_dd_moments = df_audit.sort_values('current_dd', ascending=False)['datetime'].unique()[:3]
        
        for moment in worst_dd_moments:
            matching_rows = df_audit[df_audit['datetime'] == moment]
            if matching_rows.empty: continue
            idx = matching_rows.index[0]
            
            sub_window = df_audit.iloc[max(0, idx-2):min(len(df_audit), idx+5)]
            for _, r in sub_window.iterrows():
                pnl_str = f"${r['net_pnl']:+7.2f}" if r['net_pnl'] != 0 else "    ---   "
                print(f" {r['datetime']:16s} | {r['event_type']:5s} | {r['asset']:8s} | {r['status']:4s} | {r['allocated_risk_pct']:11.2f}% | {pnl_str:10s} | x{r['firewall_scale']:.4f} |")
            print("------------------------------------------------------------------------------------------")

if __name__ == "__main__":
    analyzer = LossClusterAnalyzer()
    analyzer.execute_diagnostic_audit([2026])
