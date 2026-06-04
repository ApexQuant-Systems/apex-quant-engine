import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class AlphaSweeperMatrixEngine:
    """
    Layer 6.8: Parametric Sweeper and Portfolio Combination Grid.
    Simulates variable risk-to-reward targets across isolated and combined
    multi-asset data tracks to extract global optimal expectancy boundaries.
    """
    def __init__(self, initial_balance=30000.0):
        self.initial_balance = initial_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def generate_raw_signals(self, symbol):
        """
        Extracts pre-computed technical structures and pointer matches for an asset.
        """
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing history track: {raw_path}")
            
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
        
        df_htf['regime'] = "CHOPPY_RANGE"
        df_htf.loc[(df_htf['vol_ratio'] >= 3.0) & (df_htf['close'] > df_htf['ema_20']) & (df_htf['ema_20'] > df_htf['ema_50']), 'regime'] = "TRENDING_BULL"

        df_mtf['equilibrium'] = (df_mtf['high'].rolling(30).max() + df_mtf['low'].rolling(30).min()) / 2.0
        df_mtf['has_bull_fvg'] = False
        df_mtf.iloc[2:, df_mtf.columns.get_loc('has_bull_fvg')] = df_mtf['high'].to_numpy()[:-2] < df_mtf['low'].to_numpy()[2:]
        df_mtf['any_bull_fvg_5'] = df_mtf['has_bull_fvg'].rolling(5).max().fillna(0).astype(bool)

        h_ltf, l_ltf = df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        df_ltf['is_swing_high'] = False
        for i in range(2, len(df_ltf) - 2):
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > l_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
                
        # FIXED: Decoupled array assignment from Pandas forward-fill function
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), df_ltf['timestamp'].to_numpy(), side='right') - 1, 0, len(df_mtf) - 1)

        df_ltf['regime_htf'] = df_htf['regime'].to_numpy()[idx_htf]
        df_ltf['eq_mtf'] = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        df_ltf['bull_fvg_mtf'] = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        
        return df_ltf

    def simulate_trade_ledger(self, df_ltf, symbol, target_rr):
        """
        Simulates chronological entry/exit tracks based on a dynamic R:R metric target.
        """
        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        regimes = df_ltf['regime_htf'].to_numpy()
        equilibriums = df_ltf['eq_mtf'].to_numpy()
        fvgs = df_ltf['bull_fvg_mtf'].to_numpy()
        sh_arr = df_ltf['last_visible_sh'].to_numpy()
        time_arr = df_ltf['timestamp'].to_numpy()

        ledger = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    ledger.append({'asset': symbol, 'timestamp': time_arr[idx], 'risk_mult': -1.0, 'status': 'LOSS'})
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    ledger.append({'asset': symbol, 'timestamp': time_arr[idx], 'risk_mult': target_rr, 'status': 'WIN'})
                    active_pos = None
                continue

            if regimes[idx] == "TRENDING_BULL" and price_arr[idx] < equilibriums[idx]:
                if fvgs[idx] and not np.isnan(sh_arr[idx]) and price_arr[idx] > sh_arr[idx]:
                    sl = low_arr[idx] * 0.995
                    tp = price_arr[idx] + ((price_arr[idx] - sl) * target_rr)
                    active_pos = {'sl': sl, 'tp': tp}
        return ledger

    def evaluate_combination(self, master_ledgers, target_rr, asset_list):
        """
        Merges trade journals chronologically to determine integrated portfolio drawdown.
        """
        combined = []
        for asset in asset_list:
            combined.extend(master_ledgers[target_rr][asset])
            
        if not combined:
            return 0, 0.00, 0.00, 0.00
            
        df = pd.DataFrame(combined).sort_values('timestamp').reset_index(drop=True)
        
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        wins = len(df[df['status'] == 'WIN'])
        
        for idx, trade in df.iterrows():
            risk = balance * 0.01
            balance += risk * trade['risk_mult']
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak
            if dd > max_dd:
                max_dd = dd
                
        total_won = sum([t['risk_mult'] for t in combined if t['risk_mult'] > 0])
        total_lost = abs(sum([t['risk_mult'] for t in combined if t['risk_mult'] < 0]))
        pf = total_won / total_lost if total_lost > 0 else total_won
        win_rate = (wins / len(df)) * 100
        
        return len(df), win_rate, pf, max_dd * 100

    def run_complete_sweep(self):
        print("==========================================================================")
        print(" INITIALIZING LAYER 6.8 VECTORIZED EXHAUSTIVE ALPHA SWEEPER MATRIX")
        print("==========================================================================")
        
        assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        rr_steps = [2.0, 2.5, 3.0, 3.5, 4.0]
        
        # Load raw data tracks into memory once
        data_vault = {asset: self.generate_raw_signals(asset) for asset in assets}
        
        # Map dynamic journals across all R:R configurations
        master_ledgers = {rr: {asset: self.simulate_trade_ledger(data_vault[asset], asset, rr) for asset in assets} for rr in rr_steps}
        
        combinations = {
            "BTC ONLY": ["BTCUSDT"],
            "ETH ONLY": ["ETHUSDT"],
            "SOL ONLY": ["SOLUSDT"],
            "BTC + ETH": ["BTCUSDT", "ETHUSDT"],
            "BTC + SOL": ["BTCUSDT", "SOLUSDT"],
            "FULL PORT": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        }
        
        print("\n[✓] Matrix Generation Complete. Compiling Multi-Dimensional Readout...\n")
        
        print("====================================================================================================")
        print(f" {'COMBINATION':12s} | " + " | ".join([f"RR 1:{rr:<3} (TR / WR% / PF / DD%) " for rr in rr_steps]) + " |")
        print("====================================================================================================")
        
        for comb_name, asset_list in combinations.items():
            row_str = f" {comb_name:12s} |"
            for rr in rr_steps:
                trades, wr, pf, dd = self.evaluate_combination(master_ledgers, rr, asset_list)
                if trades == 0:
                    row_str += f" {'DORMANT':25s} |"
                else:
                    row_str += f" {trades:3d}/{wr:4.1f}%/{pf:4.2f}/{dd:4.1f}% |"
            print(row_str)
            print("----------------------------------------------------------------------------------------------------")

if __name__ == "__main__":
    sweeper = AlphaSweeperMatrixEngine()
    sweeper.run_complete_sweep()
