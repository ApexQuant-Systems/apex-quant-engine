import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.risk_engine_v2 import InstitutionalRiskEngine

class CombinedPortfolioStressTester:
    """
    Layer 6.5: Consolidated Portfolio Research Framework.
    Aggregates multi-asset trade executions into a unified chronological timeline
    to evaluate true cross-market expectancy and geometric drawdown risk.
    """
    def __init__(self, target_rr=4.0, initial_portfolio_balance=30000.0):
        self.target_rr = target_rr
        self.initial_balance = initial_portfolio_balance
        self.risk_engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
        self.instrument_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}

    def extract_raw_asset_journal(self, symbol):
        """
        Runs the pure unoptimized INTRADAY strategy across the multi-year asset file
        and returns a detailed raw chronological execution ledger.
        """
        raw_path = Path(f"./data/raw/{symbol}/{symbol}_1m_archive.csv")
        if not raw_path.exists():
            raise FileNotFoundError(f"Asset file missing: {raw_path}")
            
        df_raw = pd.read_csv(raw_path)
        df_raw['datetime'] = pd.to_datetime(df_raw['timestamp'], unit='ms', utc=True)
        df_raw = df_raw.sort_values('datetime').set_index('datetime')
        
        # Resample explicitly to Intraday Profile Nodes (4H -> 1H -> 15M)
        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_htf = df_raw.resample('4h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_mtf = df_raw.resample('1h', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        df_ltf = df_raw.resample('15min', label='right', closed='right').agg(ohlc_rules).dropna().reset_index()
        
        for df in [df_htf, df_mtf, df_ltf]:
            df['timestamp'] = (df['datetime'].astype('int64') // 10**6)

        # Pre-compute Vector Space
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
            if h_ltf[i] > h_ltf[i-1] and h_ltf[i] > h_ltf[i-2] and h_ltf[i] >= h_ltf[i+1] and h_ltf[i] >= h_ltf[i+2]:
                df_ltf.at[i, 'is_swing_high'] = True
        df_ltf['last_visible_sh'] = np.where(df_ltf['is_swing_high'].shift(2), df_ltf['high'].shift(2), np.nan)
        df_ltf['last_visible_sh'] = df_ltf['last_visible_sh'].ffill()

        # Pointer Maps
        ts_ltf = df_ltf['timestamp'].to_numpy()
        idx_htf = np.clip(np.searchsorted(df_htf['timestamp'].to_numpy(), ts_ltf, side='right') - 1, 0, len(df_htf) - 1)
        idx_mtf = np.clip(np.searchsorted(df_mtf['timestamp'].to_numpy(), ts_ltf, side='right') - 1, 0, len(df_mtf) - 1)

        price_arr, high_arr, low_arr = df_ltf['close'].to_numpy(), df_ltf['high'].to_numpy(), df_ltf['low'].to_numpy()
        regimes_htf = df_htf['regime'].to_numpy()[idx_htf]
        eq_mtf = df_mtf['equilibrium'].to_numpy()[idx_mtf]
        bull_fvg_mtf = df_mtf['any_bull_fvg_5'].to_numpy()[idx_mtf]
        ltf_sh = df_ltf['last_visible_sh'].to_numpy()
        time_arr = df_ltf['timestamp'].to_numpy()

        raw_trades = []
        active_pos = None

        for idx in range(100, len(df_ltf)):
            if active_pos:
                if low_arr[idx] <= active_pos['sl']:
                    raw_trades.append({
                        'asset': symbol, 'timestamp': time_arr[idx], 'status': 'LOSS', 
                        'risk_multiplier': -1.0
                    })
                    active_pos = None
                elif high_arr[idx] >= active_pos['tp']:
                    raw_trades.append({
                        'asset': symbol, 'timestamp': time_arr[idx], 'status': 'WIN', 
                        'risk_multiplier': self.target_rr
                    })
                    active_pos = None
                continue

            if regimes_htf[idx] == "TRENDING_BULL" and price_arr[idx] < eq_mtf[idx]:
                if bull_fvg_mtf[idx] and not np.isnan(ltf_sh[idx]) and price_arr[idx] > ltf_sh[idx]:
                    sl_price = low_arr[idx] * 0.995
                    active_pos = {'sl': sl_price, 'tp': price_arr[idx] + ((price_arr[idx] - sl_price) * self.target_rr)}

        return raw_trades

    def run_portfolio_analysis(self):
        print("==========================================================================")
        print(" INITIALIZING INTEGRATED PORTFOLIO WALK-FORWARD TESTING ENGINE")
        print("==========================================================================")
        
        assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        global_ledger = []
        
        for asset in assets:
            print(f"[*] Extracting empirical trade parameters for node: {asset}...")
            asset_trades = self.extract_raw_asset_journal(asset)
            global_ledger.extend(asset_trades)
            
        # --- THE CRITICAL ENGINE STEP: Sort every trade chronologically across all assets ---
        df_portfolio = pd.DataFrame(global_ledger)
        if df_portfolio.empty:
            print("[🛑 ERROR] Combined multi-asset ledger returned 0 total entries.")
            return
            
        df_portfolio = df_portfolio.sort_values('timestamp').reset_index(drop=True)
        
        # Chronological Equity Curve Simulation
        balance = self.initial_balance
        equity_curve = [balance]
        peak_balance = balance
        max_drawdown = 0.0
        
        for idx, trade in df_portfolio.iterrows():
            # Risk sizing layer anchored strictly to 1% of the floating balance per asset execution
            risk_capital = balance * 0.01 
            trade_pnl = risk_capital * trade['risk_multiplier']
            
            balance += trade_pnl
            equity_curve.append(balance)
            
            # Drawdown calculations
            if balance > peak_balance:
                peak_balance = balance
            current_dd = (peak_balance - balance) / peak_balance
            if current_dd > max_drawdown:
                max_drawdown = current_dd
                
            df_portfolio.at[idx, 'portfolio_balance'] = balance

        # Compute Global Consolidated Metrics
        total_trades = len(df_portfolio)
        wins = len(df_portfolio[df_portfolio['status'] == 'WIN'])
        losses = len(df_portfolio[df_portfolio['status'] == 'LOSS'])
        win_rate = (wins / total_trades) * 100
        
        # Calculate true combined Profit Factor
        total_won = sum([t['risk_multiplier'] for t in global_ledger if t['risk_multiplier'] > 0])
        total_lost = abs(sum([t['risk_multiplier'] for t in global_ledger if t['risk_multiplier'] < 0]))
        combined_pf = total_won / total_lost if total_lost > 0 else total_won

        print("\n==========================================================================")
        print(" 👑 GLOBAL COMBINED PORTFOLIO READOUT VERDICT")
        print("==========================================================================")
        print(f"  📈 Initial Inception Balance : $ {self.initial_balance:,.2f}")
        print(f"  📉 Consolidated Final Wealth : $ {balance:,.2f}")
        print(f"  🏁 Aggregated Trade Sample Size : {total_trades} trades")
        print(f"  🎯 Portfolio Win Rate Hit     : {win_rate:.2f}% (W: {wins} | L: {losses})")
        print(f"  📊 Combined Profit Factor    : {combined_pf:.2f}")
        print(f"  ⚠️ Maximum Portfolio Drawdown : {max_drawdown * 100:.2f}%")
        print("--------------------------------------------------------------------------")
        
        print("\n  [🔬 ASSET PERFORMANCE CONTRIBUTOR BREAKDOWN]")
        for asset in assets:
            sub = df_portfolio[df_portfolio['asset'] == asset]
            if not sub.empty:
                a_wins = len(sub[sub['status'] == 'WIN'])
                print(f"    │ -> {asset:9s} | Executions: {len(sub):3d} | Win Rate: {(a_wins/len(sub))*100:5.1f}%")
        print("==========================================================================")

if __name__ == "__main__":
    tester = CombinedPortfolioStressTester()
    tester.run_portfolio_analysis()
