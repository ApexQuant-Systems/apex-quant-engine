import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class PortfolioRiskFirewallEngine:
    """
    Layer 8.2: Centralized Institutional Risk Firewall and Stress Tester.
    Isolates risk budgeting to the core operating system layer. Employs a piecewise
    drawdown step-down matrix to flatten the 95th percentile tail risk boundary.
    """
    def __init__(self, initial_balance=10000.0):
        self.initial_balance = initial_balance

    def extract_base_trade_ledger(self, symbol, style_mode):
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

        # Volatility Filters
        df_htf['ema_20'] = df_htf['close'].ewm(span=20, adjust=False).mean()
        df_htf['ema_50'] = df_htf['close'].ewm(span=50, adjust=False).mean()
        h_htf, l_htf, c_htf = df_htf['high'].to_numpy(), df_htf['low'].to_numpy(), df_htf['close'].to_numpy()
        tr = np.maximum(h_htf[1:] - l_htf[1:], np.maximum(abs(h_htf[1:] - c_htf[:-1]), abs(l_htf[1:] - c_htf[:-1])))
        tr = np.insert(tr, 0, h_htf[0] - l_htf[0])
        df_htf['atr'] = pd.Series(tr).rolling(window=14).mean()
        df_htf['vol_ratio'] = (df_htf['high'].rolling(14).max() - df_htf['low'].rolling(14).min()) / (df_htf['atr'] + 1e-8)

        # Micro-Structure Targets
        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = df_mtf['high'].shift(2) < df_mtf['low']
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)
        df_mtf['struct_liq_target'] = df_mtf['high'].rolling(30).max()

        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        # FIXED: Decoupled array initialization from Series forward-fill function
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['macro_vol_ratio'] = df_htf['vol_ratio'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        df_ltf['struct_liq_mapped'] = df_mtf['struct_liq_target'].to_numpy()[idx_mtf]
        
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        vol_ratios, equilibriums = df_ltf['macro_vol_ratio'].to_numpy(), df_ltf['eq_mtf'].to_numpy()
        fvgs, sh_arr, liq_arr = df_ltf['bull_fvg_mtf'].to_numpy(), df_ltf['last_visible_sh'].to_numpy(), df_ltf['struct_liq_mapped'].to_numpy()

        raw_returns = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    raw_returns.append(-1.0)
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    raw_returns.append(active_pos['computed_rr'])
                    active_pos = None
                continue

            if vol_ratios[idx] < 3.0: continue

            if style_mode == 'PULLBACK':
                condition = price_arr[idx] < equilibriums[idx] and fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]
                sl_pad = 0.995 if symbol == 'BTCUSDT' else 0.9875
                tp_target = liq_arr[idx] if symbol == 'BTCUSDT' else price_arr[idx] + ((price_arr[idx] - (low_arr[idx] * sl_pad)) * 2.5)
            else: # MOMENTUM BREAKOUT (SOL)
                condition = price_arr[idx] > liq_arr[idx] and vol_ratios[idx] >= 3.5
                sl_pad = 0.990
                tp_target = price_arr[idx] + ((price_arr[idx] - (low_arr[idx] * sl_pad)) * 3.0)

            if condition:
                sl = low_arr[idx] * sl_pad
                risk_distance = abs(price_arr[idx] - sl)
                if risk_distance <= 0: continue
                
                if symbol == 'BTCUSDT':
                    computed_rr = (tp_target - price_arr[idx]) / risk_distance
                else:
                    computed_rr = 2.5 if style_mode == 'PULLBACK' else 3.0
                    
                if computed_rr < 1.5: continue
                active_pos = {'sl': sl, 'tp': tp_target, 'computed_rr': computed_rr}

        return raw_returns

    def compute_firewall_metrics(self, shuffle_sequence):
        """
        Processes an execution sequence through the core piecewise risk firewall.
        """
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        
        for return_multiplier in shuffle_sequence:
            if balance > peak:
                peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd:
                max_dd = current_dd

            # --- CENTRALIZED RISK FIREWALL PIECEWISE GATE ---
            if current_dd >= 0.25:
                risk_allocation = 0.0000  # Systemic Trading Halt triggered
            elif current_dd >= 0.20:
                risk_allocation = 0.0025  # Risk restricted to 0.25%
            elif current_dd >= 0.15:
                risk_allocation = 0.0050  # Risk restricted to 0.50%
            elif current_dd >= 0.10:
                risk_allocation = 0.0075  # Risk restricted to 0.75%
            else:
                risk_allocation = 0.0100  # Baseline 1.00% standard allocation

            risk_capital = balance * risk_allocation
            trade_pnl = risk_capital * return_multiplier
            balance += trade_pnl

        return max_dd * 100

    def compute_control_metrics(self, shuffle_sequence):
        """
        Processes an execution sequence through standard un-firewalled flat 1% allocation.
        """
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        
        for return_multiplier in shuffle_sequence:
            risk_capital = balance * 0.0100  # Fixed rigid 1% allocation
            trade_pnl = risk_capital * return_multiplier
            balance += trade_pnl
            
            if balance > peak:
                peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd:
                max_dd = current_dd

        return max_dd * 100

    def audit_cartridge_tail_risk(self, symbol, style_mode):
        print(f"\n[*] Running Structural Stress Audit on Cartridge Node: {symbol} ({style_mode})")
        returns = self.extract_base_trade_ledger(symbol, style_mode)
        
        if not returns:
            print(f"  └── ⚠️ Asset cartridge generated 0 trade logs.")
            return

        control_drawdowns = []
        firewall_drawdowns = []

        # Execute 1,000 parallel bootstrap shuffles
        for _ in range(1000):
            shuffle_seq = np.random.choice(returns, size=len(returns), replace=True)
            
            control_drawdowns.append(self.compute_control_metrics(shuffle_seq))
            firewall_drawdowns.append(self.compute_firewall_metrics(shuffle_seq))

        print(f"  ┌── [SAMPLE ENGINE VERIFICATION]")
        print(f"  │     └── Total Cartridge Trade Samples Compiled : {len(returns)}")
        print(f"  ├── [CONTROL TRAILING TRACK: FIXED 1% RISK]")
        print(f"  │     ├── Median Simulated Drawdown      : {np.median(control_drawdowns):.2f}%")
        print(f"  │     └── 95th Percentile Max Drawdown  : {np.percentile(control_drawdowns, 95):.2f}% 🔥")
        print(f"  └── [🔒 CENTRAL CORE FIREWALL TRACK: PIECEWISE MULTIPLIER]")
        print(f"        ├── Median Simulated Drawdown      : {np.median(firewall_drawdowns):.2f}%")
        print(f"        └── 95th Percentile Max Drawdown  : {np.percentile(firewall_drawdowns, 95):.2f}% 🛡️")
        print("--------------------------------------------------------------------------")

    def run_firewall_tournament(self):
        print("==========================================================================")
        print("    👑 APEX QUANT OS CORE: PORTFOLIO FIREWALL STRESS TOURNAMENT")
        print("==========================================================================")
        
        self.audit_cartridge_tail_risk("BTCUSDT", "PULLBACK")
        self.audit_cartridge_tail_risk("ETHUSDT", "PULLBACK")
        self.audit_cartridge_tail_risk("SOLUSDT", "MOMENTUM")
        print("==========================================================================")

if __name__ == "__main__":
    firewall = PortfolioRiskFirewallEngine()
    firewall.run_firewall_tournament()
