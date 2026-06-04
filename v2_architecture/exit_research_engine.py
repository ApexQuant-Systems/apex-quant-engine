import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class ExitEngineResearchChassis:
    """
    Layer 6.9.5: Specialized Exit Architecture Research Platform.
    Holds entries static while benchmarking variable exit models (Fixed RR, 
    Structural Liquidity Pools, Volatility Adaptive ATR) across Walk-Forward bounds.
    """
    def __init__(self, symbol="BTCUSDT", initial_balance=10000.0):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_static_entries(self):
        """
        Extracts multi-timeframe vector spaces and locks down precise trade signal locations.
        """
        raw_path = Path(f"./data/raw/{self.symbol}/{self.symbol}_1m_archive.csv")
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # 4H Volatility/Trend Pre-computation
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr_htf = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr_htf = np.insert(tr_htf, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr_htf).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)
        
        df_htf['regime'] = "CHOPPY_RANGE"
        df_htf.loc[(df_htf['vol_ratio'] >= 3.0) & (df_htf['close'] > df_htf['ema_20']) & (df_htf['ema_20'] > df_htf['ema_50']), 'regime'] = "TRENDING_BULL"

        # 1H Micro-Structure Pre-computation
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        
        # 1H Real-time Volatility and Structural High Targets
        h_mtf, l_mtf, c_mtf = df_mtf['high'].to_numpy(), df_mtf['low'].to_numpy(), df_mtf['close'].to_numpy()
        tr_mtf = np.maximum(h_mtf[1:] - l_mtf[1:], np.maximum(abs(h_mtf[1:] - c_mtf[:-1]), abs(l_mtf[1:] - c_mtf[:-1])))
        tr_mtf = np.insert(tr_mtf, 0, h_mtf[0] - l_mtf[0])
        df_mtf['atr_1h'] = pd.Series(tr_mtf).rolling(window=14).mean()
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max() # Nearest swing high target pool

        # 15M Execution Core
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

        df_ltf['regime_htf'] = df_htf['regime'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['atr_1h_mapped'] = df_mtf['atr_1h'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]
        
        return df_ltf

    def run_simulation_pass(self, df_ltf, exit_mode):
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        regimes = df_ltf['regime_htf'].to_numpy()
        equilibriums = df_ltf['eq_mtf'].to_numpy()
        fvgs = df_ltf['bull_fvg_mtf'].to_numpy()
        sh_arr = df_ltf['last_visible_sh'].to_numpy()
        atr_arr = df_ltf['atr_1h_mapped'].to_numpy()
        liq_arr = df_ltf['struct_liq_mapped'].to_numpy()
        years_arr = df_ltf['datetime'].dt.year.to_numpy()

        balance = self.initial_balance
        active_pos = None
        journal = []

        for idx in range(100, len(df_ltf)):
            current_year = years_arr[idx]
            if current_year not in [2024, 2025, 2026]:
                continue

            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    risk = balance * 0.01
                    balance -= risk
                    journal.append({'year': active_pos['year_opened'], 'status': 'LOSS', 'pnl': -risk})
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    risk = balance * 0.01
                    pnl_gain = risk * active_pos['computed_rr']
                    balance += pnl_gain
                    journal.append({'year': active_pos['year_opened'], 'status': 'WIN', 'pnl': pnl_gain})
                    active_pos = None
                continue

            if regimes[idx] == "TRENDING_BULL" and price_arr[idx] < equilibriums[idx]:
                if fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                    sl = low_arr[idx] * 0.995
                    risk_distance = price_arr[idx] - sl
                    if risk_distance <= 0:
                        continue
                        
                    # --- EXECUTION CARTRIDGE TARGET ROUTING INTERCEPT ---
                    if exit_mode == 'FIXED_RR':
                        tp = price_arr[idx] + (risk_distance * 3.0)
                        computed_rr = 3.0
                    elif exit_mode == 'STRUCTURE_LIQ':
                        tp = liq_arr[idx]
                        computed_rr = (tp - price_arr[idx]) / risk_distance
                        if computed_rr < 1.5: # Hard institutional floor filter
                            continue
                    elif exit_mode == 'ATR_DYNAMIC':
                        tp = price_arr[idx] + (atr_arr[idx] * 3.5)
                        computed_rr = (tp - price_arr[idx]) / risk_distance
                        if computed_rr < 1.5:
                            continue

                    active_pos = {
                        'sl': sl, 'tp': tp, 'computed_rr': computed_rr, 'year_opened': current_year
                    }

        return journal

    def benchmark_exit_architectures(self):
        print("==========================================================================")
        print(f" LAUNCHING APEX QUANT OS V2: EXIT ARCHITECTURE TOURNAMENT ({self.symbol})")
        print("==========================================================================")
        
        df_signals = self.generate_static_entries()
        exit_modes = ['FIXED_RR', 'STRUCTURE_LIQ', 'ATR_DYNAMIC']
        
        for mode in exit_modes:
            journal = self.run_simulation_pass(df_signals, mode)
            print(f"\n[🔬 EXIT ENGINE CONFIGURATION: {mode}]")
            
            if not journal:
                print("  └── ⚠️ Dormant strategy trace. No opportunities compiled.")
                continue
                
            df_j = pd.DataFrame(journal)
            
            # Segment analysis matrices chronologically
            for epoch_name, epochs in [("In-Sample (2024-2025)", [2024, 2025]), ("Out-of-Sample (2026)", [2026])]:
                sub = df_j[df_j['year'].isin(epochs)]
                if sub.empty:
                    print(f"  ├── {epoch_name:23s} : 0 Trades | PF: 0.00 | Net: $0.00")
                    continue
                    
                total_trades = len(sub)
                wins = len(sub[sub['status'] == 'WIN'])
                wr = (wins / total_trades) * 100
                total_won = sub[sub['pnl'] > 0]['pnl'].sum()
                total_lost = abs(sub[sub['pnl'] < 0]['pnl'].sum())
                pf = total_won / total_lost if total_lost > 0 else total_won
                net_return = sub['pnl'].sum()
                
                status_icon = "🟢" if pf >= 1.20 else ("🟡" if pf >= 1.00 else "🔴")
                print(f"  ├── {epoch_name:23s} : {total_trades:2d} Trades | Win Rate: {wr:4.1f}% | Profit Factor: {pf:.2f} | PnL: {net_return:+,.2f} {status_icon}")
        print("==========================================================================")

if __name__ == "__main__":
    runner = ExitEngineResearchChassis()
    runner.benchmark_exit_architectures()
