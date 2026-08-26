import sys
import os
import pandas as pd
import numpy as np
import time

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core_vNext.strategy.unified_strategy import UnifiedStrategy
from core_vNext.strategy.strategy_state_machine import StrategyState

class VNextGridSearch:
    def __init__(self, data_path: str, asset: str = "BTCUSDT", initial_capital: float = 10000.0):
        self.data_path = data_path
        self.asset = asset
        self.initial_capital = initial_capital
        self.df_htf = None
        self.df_mtf = None
        self.df_ltf = None

    def load_and_resample(self):
        print(f"Loading data from {self.data_path}...")
        df = pd.read_csv(self.data_path)
        
        try:
            if df['timestamp'].dtype in [np.int64, np.float64] and df['timestamp'].iloc[0] > 1e11:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['datetime'] = pd.to_datetime(df['timestamp'])
        except Exception:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            
        df.set_index('datetime', inplace=True)
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        print("Resampling to HTF (4H), MTF (1H), LTF (15M)...")
        df_htf = df.resample('4h').agg(ohlc_dict).dropna()
        df_htf['timestamp'] = df_htf.index.view('int64') // 10**6
        
        df_mtf = df.resample('1h').agg(ohlc_dict).dropna()
        df_mtf['timestamp'] = df_mtf.index.view('int64') // 10**6
        
        df_ltf = df.resample('15min').agg(ohlc_dict).dropna()
        df_ltf['timestamp'] = df_ltf.index.view('int64') // 10**6
        
        self.df_htf = df_htf.reset_index()
        self.df_mtf = df_mtf.reset_index()
        self.df_ltf = df_ltf.reset_index()

    def run_simulation(self, htf_k, mtf_k, ltf_k):
        capital = self.initial_capital
        strategy = UnifiedStrategy(self.asset, "SET_4", htf_k, mtf_k, ltf_k)
        trades = []
        in_trade = False
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        partial_tp_price = 0.0
        position_size = 0.0
        has_taken_partial = False
        
        for i in range(100, len(self.df_ltf)):
            current_time = self.df_ltf.iloc[i]['datetime']
            current_close = self.df_ltf.iloc[i]['close']
            current_high = self.df_ltf.iloc[i]['high']
            current_low = self.df_ltf.iloc[i]['low']
            
            if in_trade:
                side = strategy.fsm.active_intent.side.name
                
                # Partial TP check
                if not has_taken_partial:
                    if side == 'LONG' and current_high >= partial_tp_price:
                        profit = (partial_tp_price - entry_price) * (position_size * 0.5)
                        capital += profit
                        position_size *= 0.5
                        sl_price = max(sl_price, entry_price)
                        has_taken_partial = True
                        trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': profit, 'capital': capital})
                    elif side == 'SHORT' and current_low <= partial_tp_price:
                        profit = (entry_price - partial_tp_price) * (position_size * 0.5)
                        capital += profit
                        position_size *= 0.5
                        sl_price = min(sl_price, entry_price)
                        has_taken_partial = True
                        trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': profit, 'capital': capital})
                
                # SL and TP check
                if side == 'LONG':
                    if current_low <= sl_price:
                        loss = (sl_price - entry_price) * position_size
                        capital += loss
                        in_trade = False
                        has_taken_partial = False
                        strategy.fsm.reset()
                        trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': loss, 'capital': capital})
                    elif current_high >= tp_price:
                        profit = (tp_price - entry_price) * position_size
                        capital += profit
                        in_trade = False
                        has_taken_partial = False
                        strategy.fsm.reset()
                        trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': profit, 'capital': capital})
                else: # SHORT
                    if current_high >= sl_price:
                        loss = (entry_price - sl_price) * position_size
                        capital += loss
                        in_trade = False
                        has_taken_partial = False
                        strategy.fsm.reset()
                        trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': loss, 'capital': capital})
                    elif current_low <= tp_price:
                        profit = (entry_price - tp_price) * position_size
                        capital += profit
                        in_trade = False
                        has_taken_partial = False
                        strategy.fsm.reset()
                        trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': profit, 'capital': capital})
                
                # Check MTF trailing logic
                if in_trade:
                    if side == 'LONG' and strategy.mtf_swings.last_confirmed_low:
                        new_sl = strategy.mtf_swings.last_confirmed_low.price
                        if new_sl > sl_price:
                            sl_price = new_sl
                    elif side == 'SHORT' and strategy.mtf_swings.last_confirmed_high:
                        new_sl = strategy.mtf_swings.last_confirmed_high.price
                        if new_sl < sl_price:
                            sl_price = new_sl
                        
                continue 

            htf_window = self.df_htf[self.df_htf['datetime'] <= current_time].tail(150)
            mtf_window = self.df_mtf[self.df_mtf['datetime'] <= current_time].tail(50)
            ltf_window = self.df_ltf.iloc[i-50:i+1]
            
            if len(htf_window) < 10 or len(mtf_window) < 10:
                continue

            strategy.process_multi_horizon(htf_window, mtf_window, ltf_window)
            
            if strategy.fsm.state == StrategyState.ORDER_SUBMITTED:
                intent = strategy.fsm.active_intent
                
                in_trade = True
                entry_price = current_close
                sl_price = intent.sl_price
                tp_price = intent.tp_price
                has_taken_partial = False
                
                risk_dist = abs(entry_price - sl_price)
                if risk_dist > 0:
                    position_size = (capital * intent.risk_percentage) / risk_dist
                    if intent.side.name == 'LONG':
                        partial_tp_price = entry_price + (risk_dist * 2.0)
                    else:
                        partial_tp_price = entry_price - (risk_dist * 2.0)
                else:
                    in_trade = False
                    
                trades.append({'time': current_time, 'type': 'ENTRY', 'side': intent.side.name, 'price': entry_price, 'sl': sl_price, 'tp': tp_price})
                strategy.fsm.transition_to(StrategyState.POSITION_ACTIVE)

        exits = [t for t in trades if t['type'].startswith('EXIT_SL') or t['type'].startswith('EXIT_TP')]
        wins = [t for t in exits if t['pnl'] > 0]
        be_trades = [t for t in exits if t['pnl'] == 0]
        non_losses = len(wins) + len(be_trades)
        win_rate = (non_losses / len(exits)) * 100 if len(exits) > 0 else 0
        
        return {
            'htf_k': htf_k,
            'mtf_k': mtf_k,
            'ltf_k': ltf_k,
            'final_capital': capital,
            'total_trades': len(exits),
            'win_rate': win_rate
        }

if __name__ == "__main__":
    harness = VNextGridSearch("data/raw/BTCUSDT_2023.csv")
    harness.load_and_resample()
    
    # 4 Configurations
    configs = [
        (3, 3, 2), # Base
        (4, 3, 2),
        (5, 4, 3),
        (6, 5, 3)
    ]
    
    results = []
    print("\n--- RUNNING PARAMETER GRID SEARCH ---")
    start_t = time.time()
    for cfg in configs:
        print(f"Testing Config: HTF_k={cfg[0]}, MTF_k={cfg[1]}, LTF_k={cfg[2]} ...")
        res = harness.run_simulation(*cfg)
        results.append(res)
        print(f"  Result: Trades={res['total_trades']}, WinRate={res['win_rate']:.2f}%, Final Cap=${res['final_capital']:.2f}")
        
    end_t = time.time()
    
    print("\n--- BEST CONFIGURATION ---")
    best_config = max(results, key=lambda x: x['final_capital'])
    print(f"HTF_k={best_config['htf_k']}, MTF_k={best_config['mtf_k']}, LTF_k={best_config['ltf_k']}")
    print(f"Final Capital: ${best_config['final_capital']:,.2f}")
    print(f"Win Rate:      {best_config['win_rate']:.2f}%")
    print(f"Total Trades:  {best_config['total_trades']}")
    print(f"\nTotal Search Time: {end_t - start_t:.2f} seconds")
