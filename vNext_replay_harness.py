import sys
import os
import pandas as pd
import numpy as np
import time

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core_vNext.strategy.unified_strategy import UnifiedStrategy
from core_vNext.strategy.strategy_state_machine import StrategyState

class VNextHarness:
    def __init__(self, data_path: str, asset: str = "BTCUSDT", initial_capital: float = 10000.0):
        self.data_path = data_path
        self.asset = asset
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.strategy = UnifiedStrategy(asset, "SET_4")
        self.trades = []
        self.in_trade = False
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.partial_tp_price = 0.0
        self.position_size = 0.0
        self.has_taken_partial = False

    def load_and_resample(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        print(f"Loading data from {self.data_path}...")
        df = pd.read_csv(self.data_path)
        
        # In legacy system this threw "could not convert string to float: '2018-01-01 00:00:00+00:00'"
        # We handle timestamp explicitly here
        try:
            # If timestamp is ms
            if df['timestamp'].dtype in [np.int64, np.float64] and df['timestamp'].iloc[0] > 1e11:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['datetime'] = pd.to_datetime(df['timestamp'])
        except Exception as e:
            print(f"Timestamp parsing error: {e}")
            df['datetime'] = pd.to_datetime(df['timestamp'])
            
        df.set_index('datetime', inplace=True)
        
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        print("Resampling to HTF (4H), MTF (1H), LTF (15M)...")
        # Ensure we drop NaNs that appear during resampling empty periods
        df_htf = df.resample('4h').agg(ohlc_dict).dropna()
        df_htf['timestamp'] = df_htf.index.view('int64') // 10**6
        
        df_mtf = df.resample('1h').agg(ohlc_dict).dropna()
        df_mtf['timestamp'] = df_mtf.index.view('int64') // 10**6
        
        df_ltf = df.resample('15min').agg(ohlc_dict).dropna()
        df_ltf['timestamp'] = df_ltf.index.view('int64') // 10**6
        
        return df_htf.reset_index(), df_mtf.reset_index(), df_ltf.reset_index()

    def run(self):
        df_htf, df_mtf, df_ltf = self.load_and_resample()
        
        print(f"Commencing Backtest Simulation over {len(df_ltf)} LTF bars...")
        start_t = time.time()
        
        # Step through LTF data
        # We use a sliding window of 100 bars for performance, as k=3 lookbacks don't need infinite history
        for i in range(100, len(df_ltf)):
            if i % 1000 == 0:
                print(f"Processed {i}/{len(df_ltf)} bars...")
                
            current_time = df_ltf.iloc[i]['datetime']
            current_close = df_ltf.iloc[i]['close']
            current_high = df_ltf.iloc[i]['high']
            current_low = df_ltf.iloc[i]['low']
            
            # Position management
            if self.in_trade:
                side = self.strategy.fsm.active_intent.side.name
                
                # Partial TP check
                if not self.has_taken_partial:
                    if side == 'LONG' and current_high >= self.partial_tp_price:
                        profit = (self.partial_tp_price - self.entry_price) * (self.position_size * 0.5)
                        self.capital += profit
                        self.position_size *= 0.5
                        self.sl_price = max(self.sl_price, self.entry_price)
                        self.has_taken_partial = True
                        self.trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': profit, 'capital': self.capital})
                    elif side == 'SHORT' and current_low <= self.partial_tp_price:
                        profit = (self.entry_price - self.partial_tp_price) * (self.position_size * 0.5)
                        self.capital += profit
                        self.position_size *= 0.5
                        self.sl_price = min(self.sl_price, self.entry_price)
                        self.has_taken_partial = True
                        self.trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': profit, 'capital': self.capital})
                
                # SL and TP check
                if side == 'LONG':
                    if current_low <= self.sl_price:
                        loss = (self.sl_price - self.entry_price) * self.position_size
                        self.capital += loss
                        self.in_trade = False
                        self.has_taken_partial = False
                        self.strategy.fsm.reset()
                        self.trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': loss, 'capital': self.capital})
                    elif current_high >= self.tp_price:
                        profit = (self.tp_price - self.entry_price) * self.position_size
                        self.capital += profit
                        self.in_trade = False
                        self.has_taken_partial = False
                        self.strategy.fsm.reset()
                        self.trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': profit, 'capital': self.capital})
                else: # SHORT
                    if current_high >= self.sl_price:
                        loss = (self.entry_price - self.sl_price) * self.position_size
                        self.capital += loss
                        self.in_trade = False
                        self.has_taken_partial = False
                        self.strategy.fsm.reset()
                        self.trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': loss, 'capital': self.capital})
                    elif current_low <= self.tp_price:
                        profit = (self.entry_price - self.tp_price) * self.position_size
                        self.capital += profit
                        self.in_trade = False
                        self.has_taken_partial = False
                        self.strategy.fsm.reset()
                        self.trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': profit, 'capital': self.capital})
                
                # Check MTF trailing logic (Simulated here)
                if self.in_trade:
                    if side == 'LONG' and self.strategy.mtf_swings.last_confirmed_low:
                        new_sl = self.strategy.mtf_swings.last_confirmed_low.price
                        if new_sl > self.sl_price:
                            self.sl_price = new_sl
                    elif side == 'SHORT' and self.strategy.mtf_swings.last_confirmed_high:
                        new_sl = self.strategy.mtf_swings.last_confirmed_high.price
                        if new_sl < self.sl_price:
                            self.sl_price = new_sl
                        
                continue # Skip searching for new trades if in trade

            # Slicing up to current time (Optimized for performance by slicing with .iloc based on known frequency ratios)
            # 1 LTF bar (15m) -> 4 per hour -> 16 per 4H
            htf_window = df_htf[df_htf['datetime'] <= current_time].tail(150)
            mtf_window = df_mtf[df_mtf['datetime'] <= current_time].tail(50)
            ltf_window = df_ltf.iloc[i-50:i+1]
            
            if len(htf_window) < 10 or len(mtf_window) < 10:
                continue

            self.strategy.process_multi_horizon(htf_window, mtf_window, ltf_window)
            
            if self.strategy.fsm.state == StrategyState.ORDER_SUBMITTED:
                intent = self.strategy.fsm.active_intent
                
                self.in_trade = True
                self.entry_price = current_close
                self.sl_price = intent.sl_price
                self.tp_price = intent.tp_price
                self.has_taken_partial = False
                
                # Risk modeling
                risk_dist = abs(self.entry_price - self.sl_price)
                if risk_dist > 0:
                    self.position_size = (self.capital * intent.risk_percentage) / risk_dist
                    if intent.side.name == 'LONG':
                        self.partial_tp_price = self.entry_price + (risk_dist * 2.0)
                    else:
                        self.partial_tp_price = self.entry_price - (risk_dist * 2.0)
                else:
                    self.in_trade = False
                    
                self.trades.append({'time': current_time, 'type': 'ENTRY', 'side': intent.side.name, 'price': self.entry_price, 'sl': self.sl_price, 'tp': self.tp_price})
                self.strategy.fsm.transition_to(StrategyState.POSITION_ACTIVE)

        end_t = time.time()
        print("\n" + "=" * 50)
        print("🚀 APEX VNEXT BACKTEST COMPLETE")
        print("=" * 50)
        print(f"Simulation Time: {end_t - start_t:.2f} seconds")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital:   ${self.capital:,.2f}")
        
        exits = [t for t in self.trades if t['type'].startswith('EXIT_SL') or t['type'].startswith('EXIT_TP')]
        partials = [t for t in self.trades if t['type'] == 'EXIT_PARTIAL_TP']
        wins = [t for t in exits if t['pnl'] > 0]
        losses = [t for t in exits if t['pnl'] < 0]
        be_trades = [t for t in exits if t['pnl'] == 0]
        
        print(f"Total Completed Trades: {len(exits)}")
        print(f"Wins (Hit 4R TP):       {len(wins)}")
        print(f"Losses (Hit SL):        {len(losses)}")
        print(f"Break-Evens:            {len(be_trades)}")
        print(f"Partials Secured (2R):  {len(partials)}")
        
        # A win in this context is any trade that didn't end in a loss (e.g., hit 2R and stopped at BE)
        non_losses = len(wins) + len(be_trades)
        if len(exits) > 0:
            print(f"Win Rate (Non-Loss):    {(non_losses/len(exits))*100:.2f}%")
            
        print("=" * 50)

if __name__ == "__main__":
    harness = VNextHarness("data/raw/BTCUSDT_2023.csv")
    harness.run()
