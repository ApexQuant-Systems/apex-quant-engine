import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Maintain absolute path configuration across local workspaces
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v2_architecture.unified_portfolio_validator import UnifiedPortfolioValidator

class PortfolioEventEngine(UnifiedPortfolioValidator):
    """
    Layer 9.5: Discrete Event-Driven Portfolio Simulation Chassis.
    Re-architects the execution loop around an unbroken chronological event grid,
    clearing expired positions on their exact exit timestamps and dynamically 
    scaling risk parameters via fractional heat modeling.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance)
        self.max_portfolio_heat = max_portfolio_heat
        self.cartridge_confidence = {"BTCUSDT": 95, "SOLUSDT": 85, "ETHUSDT": 70}

    def extract_cartridge_trades(self, symbol):
        """
        Explicitly overrides base method to patch the entry_timestamp tracking footprint.
        """
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
                    'asset': symbol, 'entry_timestamp': int(time_arr[idx]), 'exit_date': None, 'exit_timestamp': 0,
                    'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'risk_mult': 0.0,
                    'regime': regime_tag, 'year': int(years_arr[idx])
                }
        return trades

    def execute_event_driven_simulation(self, global_ledger, target_years):
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        
        wins, losses = 0, 0
        total_pnl_won, total_pnl_lost = 0.0, 0.0
        active_positions = []
        
        df_ledger = pd.DataFrame(global_ledger)
        df_ledger = df_ledger[df_ledger['year'].isin(target_years)]
        
        if df_ledger.empty:
            return 0, 0.0, 0.0, balance, 0.0

        # Create sequential structural grid mapping all entries and exits chronologically
        unified_timeline = sorted(list(set(df_ledger['entry_timestamp'].tolist() + df_ledger['exit_timestamp'].tolist())))

        for current_tick in unified_timeline:
            still_active = []
            
            # 1. Sequential Position Closing Loop
            for pos in active_positions:
                if current_tick >= pos['exit_timestamp']:
                    trade_pnl = pos['allocated_risk_capital'] * pos['risk_mult']
                    balance += trade_pnl
                    
                    if trade_pnl > 0:
                        wins += 1; total_pnl_won += trade_pnl
                    else:
                        losses += 1; total_pnl_lost += abs(trade_pnl)
                else:
                    still_active.append(pos)
            active_positions = still_active

            current_heat = sum([p['risk_budget_pct'] for p in active_positions])
            available_heat = self.max_portfolio_heat - current_heat

            if balance > peak: peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd: max_dd = current_dd

            # 2. Sequential Capital Allocation Loop
            concurrent_signals = df_ledger[df_ledger['entry_timestamp'] == current_tick].to_dict('records')
            if not concurrent_signals or available_heat <= 0: continue

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

                if current_dd >= 0.25: risk_scale = 0.0000
                elif current_dd >= 0.20: risk_scale = 0.0025
                elif current_dd >= 0.15: risk_scale = 0.0050
                elif current_dd >= 0.10: risk_scale = 0.0075
                else: risk_scale = 1.0000

                final_risk_pct = allocated_risk * risk_scale
                if final_risk_pct <= 0: continue

                candidate['risk_budget_pct'] = final_risk_pct
                candidate['allocated_risk_capital'] = balance * final_risk_pct
                
                active_positions.append(candidate)
                available_heat -= final_risk_pct

        total_trades = wins + losses
        net_pf = total_pnl_won / total_pnl_lost if total_pnl_lost > 0 else total_pnl_won
        recovery_factor = (balance - self.initial_balance) / (self.initial_balance * max_dd + 1e-8)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        
        return total_trades, win_rate, net_pf, max_dd * 100, balance, recovery_factor

    def run_event_engine_audit(self):
        print("==========================================================================================")
        print(" 🔒 APEX QUANT OS CORE: DISCRETE EVENT-DRIVEN CHRONOLOGICAL PORTFOLIO CORE")
        print("==========================================================================================")
        
        global_ledger = []
        for asset in self.assets:
            trades = self.extract_cartridge_trades(asset)
            global_ledger.extend(trades)
            
        global_ledger = sorted(global_ledger, key=lambda x: x['entry_timestamp'])

        print("\n[EVALUATING ARRAYS OVER UN-BLINDED 2026 OUT-OF-SAMPLE FRONTIER VIA MARKET CLOCK]")
        print("------------------------------------------------------------------------------------------")
        
        control_weights = {"BTCUSDT": 0.33, "ETHUSDT": 0.33, "SOLUSDT": 0.33}
        c_tr, c_wr, c_pf, c_dd, c_bal, c_rf = self.execute_timeline_simulation(global_ledger, control_weights, self.initial_balance, [2026])
        
        e_tr, e_wr, e_pf, e_dd, e_bal, e_rf = self.execute_event_driven_simulation(global_ledger, [2026])
        
        print(f"▶️ CONTROL PATH (UN-SCHEDULED SEQUENTIAL PASS):")
        print(f"  ├── Total Completed Trades: {c_tr} Trades | Win Rate: {c_wr:.1f}%")
        print(f"  └── Net Profit Factor     : {c_pf:.2f} | Max Drawdown: {c_dd:.1f}% | Recovery Factor: {c_rf:.2f}")
        print(f"")
        print(f"▶️🔒 EVENT-DRIVEN CHRONO PATH (V2 DISCRETE ENGINE):")
        print(f"  ├── Total Scheduled Trades: {e_tr} Trades | Win Rate: {e_wr:.1f}%")
        print(f"  └── Net Profit Factor     : {e_pf:.2f} | Max Drawdown: {e_dd:.1f}% | Recovery Factor: {e_rf:.2f}")
        
        status = "🟢 [VALIDATED] Event-driven clock successfully optimized systemic drawdown and expectancy." if e_rf > c_rf else "🔴 [CRITICAL] Core asset timeline distortion detected."
        print(f"\nSYSTEM VERDICT: {status}")
        print("==========================================================================================")

if __name__ == "__main__":
    engine = PortfolioEventEngine()
    engine.run_event_engine_audit()
