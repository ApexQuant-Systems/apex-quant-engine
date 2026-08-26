import sys
import os
import time
import pandas as pd
import numpy as np
import pandas_ta as ta
from dataclasses import dataclass
from typing import Dict, List, Optional

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core_vNext.structure.swing_engine import SwingEngine, Trend
from core_vNext.risk.dynamic_volatility_sizer import DynamicVolatilitySizer
from core_vNext.portfolio.portfolio_allocator import PortfolioHeatGovernor

@dataclass
class VolatilitySmoothedResult:
    asset: str
    set_name: str
    htf_tf: str
    mtf_tf: str
    ltf_tf: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    net_profit: float
    net_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    total_trades: int
    wins_4r: int
    losses_1r: int
    win_rate: float
    profit_factor: float

class InstitutionalVolatilityMasterMatrix:
    def __init__(self, initial_capital_per_cartridge: float = 10000.0):
        self.initial_capital = initial_capital_per_cartridge
        self.taker_fee_pct = 0.0004   # 0.04% Taker Fee
        self.slippage_pct = 0.0002    # 0.02% Slippage
        
        self.vol_sizer = DynamicVolatilitySizer(target_base_risk_pct=0.012, min_risk_pct=0.004, max_risk_pct=0.018)
        self.governor = PortfolioHeatGovernor(max_total_portfolio_heat_pct=0.025, max_daily_drawdown_pct=0.025)
        
        self.assets = {
            "BTCUSDT": "data/archives/BTCUSDT_final_compliance.csv",
            "ETHUSDT": "data/archives/ETHUSDT_final_compliance.csv",
            "SOLUSDT": "data/archives/SOLUSDT_final_compliance.csv"
        }
        
        self.timeframe_sets = {
            "SET_1_MACRO_INVESTING":     {"htf": "1ME", "mtf": "1W",  "ltf": "1D",    "min_sl": 0.015, "max_sl": 0.200},
            "SET_2_MEDIUM_SWING":        {"htf": "1W",  "mtf": "1D",  "ltf": "4h",    "min_sl": 0.012, "max_sl": 0.100},
            "SET_3_POSITION_PLAY":        {"htf": "1D",  "mtf": "4h",  "ltf": "1h",    "min_sl": 0.008, "max_sl": 0.050},
            "SET_4_INTRADAY_EXPANSION":   {"htf": "4h",  "mtf": "1h",  "ltf": "15min", "min_sl": 0.006, "max_sl": 0.035}
        }
        
        self.cached_downsamples: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.cached_swings: Dict[str, Dict[str, tuple]] = {}
        self.cached_atr: Dict[str, Dict[str, np.ndarray]] = {}

    def load_and_downsample_asset(self, asset: str):
        if asset in self.cached_downsamples:
            return self.cached_downsamples[asset]
            
        filepath = self.assets[asset]
        print(f"\n[📥 INGESTING ARCHIVE] {asset} -> {filepath}...")
        t0 = time.time()
        df = pd.read_csv(filepath, usecols=[0, 2, 3, 4, 5, 6], names=['datetime', 'open', 'high', 'low', 'close', 'volume'], header=0)
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        df = df.sort_values('datetime').set_index('datetime')
        print(f"  └─ Loaded {len(df):,} 1m bars in {time.time()-t0:.2f}s.")
        
        ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        t1 = time.time()
        
        ds = {
            "15min": df.resample('15min').agg(ohlc).dropna(),
            "1h":    df.resample('1h').agg(ohlc).dropna(),
            "4h":    df.resample('4h').agg(ohlc).dropna(),
            "1D":    df.resample('1D').agg(ohlc).dropna(),
            "1W":    df.resample('1W').agg(ohlc).dropna(),
            "1ME":   df.resample('1ME').agg(ohlc).dropna()
        }
        
        self.cached_atr[asset] = {}
        for tf, frame in ds.items():
            frame['timestamp'] = frame.index.view('int64') // 10**6
            frame['vol_sma'] = frame['volume'].rolling(20).mean().fillna(frame['volume'])
            frame['ema20'] = frame['close'].ewm(span=20).mean()
            frame['ema50'] = frame['close'].ewm(span=50).mean()
            
            # ATR
            if len(frame) >= 15:
                atr_s = frame.ta.atr(length=14)
                self.cached_atr[asset][tf] = atr_s.fillna(frame['close'] * 0.01).values
            else:
                self.cached_atr[asset][tf] = (frame['close'] * 0.01).values
                
            ds[tf] = frame.reset_index()
            
        # Precompute Swings
        self.cached_swings[asset] = {}
        for tf, frame in ds.items():
            k = 2 if tf in ['15min', '1h'] else 3
            engine = SwingEngine(k=k)
            trends = []
            last_highs = []
            last_lows = []
            highs = frame['high'].values
            lows = frame['low'].values
            closes = frame['close'].values
            timestamps = frame['timestamp'].values
            
            for i in range(len(frame)):
                if i >= k:
                    engine._evaluate_step(i, timestamps, highs, lows, closes)
                trends.append(engine.current_trend)
                last_highs.append(engine.last_confirmed_high)
                last_lows.append(engine.last_confirmed_low)
            self.cached_swings[asset][tf] = (trends, last_highs, last_lows)
            
        self.cached_downsamples[asset] = ds
        return ds

    def run_single_simulation(self, asset: str, set_name: str, config: dict, ds: Dict[str, pd.DataFrame]) -> VolatilitySmoothedResult:
        htf_tf = config['htf']
        mtf_tf = config['mtf']
        ltf_tf = config['ltf']
        min_sl = config['min_sl']
        max_sl = config['max_sl']
        
        df_htf = ds[htf_tf]
        df_mtf = ds[mtf_tf]
        df_ltf = ds[ltf_tf]
        
        htf_trends, _, _ = self.cached_swings[asset][htf_tf]
        mtf_trends, _, _ = self.cached_swings[asset][mtf_tf]
        ltf_trends, ltf_highs, ltf_lows = self.cached_swings[asset][ltf_tf]
        
        htf_ema20 = df_htf['ema20'].values
        htf_ema50 = df_htf['ema50'].values
        ltf_atr = self.cached_atr[asset][ltf_tf]
        median_atr = np.median(ltf_atr)
        
        if len(df_ltf) < 50:
            return None
            
        htf_ts = df_htf['datetime'].values
        mtf_ts = df_mtf['datetime'].values
        ltf_ts = df_ltf['datetime'].values
        
        htf_idx_map = np.searchsorted(htf_ts, ltf_ts, side='right') - 1
        mtf_idx_map = np.searchsorted(mtf_ts, ltf_ts, side='right') - 1
        
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0
        daily_equity = {}
        
        trades = []
        in_trade = False
        side = 'LONG'
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        partial_tp_price = 0.0
        position_size = 0.0
        has_taken_partial = False
        
        warmup = max(30, min(100, len(df_ltf) // 10))
        
        closes = df_ltf['close'].values
        highs = df_ltf['high'].values
        lows = df_ltf['low'].values
        opens = df_ltf['open'].values
        volumes = df_ltf['volume'].values
        vol_smas = df_ltf['vol_sma'].values
        datetimes = df_ltf['datetime'].values
        
        for i in range(warmup, len(df_ltf)):
            current_time = datetimes[i]
            current_date = str(current_time)[:10]
            
            c = closes[i]
            h = highs[i]
            l = lows[i]
            o = opens[i]
            v = volumes[i]
            vsma = vol_smas[i]
            cur_atr = ltf_atr[i]
            
            h_idx = max(0, htf_idx_map[i])
            m_idx = max(0, mtf_idx_map[i])
            
            htf_t = htf_trends[h_idx]
            mtf_t = mtf_trends[m_idx]
            ltf_t = ltf_trends[i]
            
            ema20 = htf_ema20[h_idx]
            ema50 = htf_ema50[h_idx]
            
            # Position management
            if in_trade:
                if not has_taken_partial:
                    if side == 'LONG' and h >= partial_tp_price:
                        realized_exit = partial_tp_price * (1.0 - self.slippage_pct)
                        fee_exit = realized_exit * (position_size * 0.5) * self.taker_fee_pct
                        net_pnl = ((realized_exit - entry_price) * (position_size * 0.5)) - fee_exit
                        capital += net_pnl
                        position_size *= 0.5
                        sl_price = entry_price * 1.002
                        has_taken_partial = True
                        trades.append({'pnl': net_pnl, 'type': 'PARTIAL'})
                    elif side == 'SHORT' and l <= partial_tp_price:
                        realized_exit = partial_tp_price * (1.0 + self.slippage_pct)
                        fee_exit = realized_exit * (position_size * 0.5) * self.taker_fee_pct
                        net_pnl = ((entry_price - realized_exit) * (position_size * 0.5)) - fee_exit
                        capital += net_pnl
                        position_size *= 0.5
                        sl_price = entry_price * 0.998
                        has_taken_partial = True
                        trades.append({'pnl': net_pnl, 'type': 'PARTIAL'})
                        
                if side == 'LONG':
                    if l <= sl_price:
                        realized_exit = sl_price * (1.0 - self.slippage_pct)
                        fee_exit = realized_exit * position_size * self.taker_fee_pct
                        net_pnl = ((realized_exit - entry_price) * position_size) - fee_exit
                        capital += net_pnl
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net_pnl, 'type': 'SL_OR_BE'})
                    elif h >= tp_price:
                        realized_exit = tp_price * (1.0 - self.slippage_pct)
                        fee_exit = realized_exit * position_size * self.taker_fee_pct
                        net_pnl = ((realized_exit - entry_price) * position_size) - fee_exit
                        capital += net_pnl
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net_pnl, 'type': 'TP'})
                else:
                    if h >= sl_price:
                        realized_exit = sl_price * (1.0 + self.slippage_pct)
                        fee_exit = realized_exit * position_size * self.taker_fee_pct
                        net_pnl = ((entry_price - realized_exit) * position_size) - fee_exit
                        capital += net_pnl
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net_pnl, 'type': 'SL_OR_BE'})
                    elif l <= tp_price:
                        realized_exit = tp_price * (1.0 + self.slippage_pct)
                        fee_exit = realized_exit * position_size * self.taker_fee_pct
                        net_pnl = ((entry_price - realized_exit) * position_size) - fee_exit
                        capital += net_pnl
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net_pnl, 'type': 'TP'})
                        
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100
                if dd > max_drawdown:
                    max_drawdown = dd
                daily_equity[current_date] = capital
                continue
                
            # Entry logic
            if not in_trade:
                if htf_t == Trend.BULLISH and ema20 > ema50 and mtf_t == Trend.BULLISH and ltf_t == Trend.BULLISH:
                    body = abs(c - o)
                    candle_range = max(0.01, h - l)
                    if (body / candle_range) >= 0.50 and v >= (vsma * 1.05) and c > o:
                        ltf_l = ltf_lows[i]
                        if ltf_l and ltf_l.price < c:
                            sl = ltf_l.price
                            risk_dist = c - sl
                            sl_pct = risk_dist / c
                            if min_sl <= sl_pct <= max_sl:
                                # Apply Dynamic Volatility Position Sizer
                                pos_sz, d_risk, eff_risk = self.vol_sizer.compute_volatility_adjusted_size(
                                    current_equity=capital,
                                    entry_price=c,
                                    sl_price=sl,
                                    current_atr=cur_atr,
                                    median_atr=median_atr
                                )
                                if pos_sz > 0 and self.governor.can_open_new_trade(asset, eff_risk, capital, current_date):
                                    tp = c + (risk_dist * 4.0)
                                    in_trade = True
                                    side = 'LONG'
                                    entry_price = c
                                    sl_price = sl
                                    tp_price = tp
                                    partial_tp_price = c + (risk_dist * 2.0)
                                    position_size = pos_sz
                                    fee_entry = entry_price * position_size * self.taker_fee_pct
                                    capital -= fee_entry
                                    has_taken_partial = False
                                    trades.append({'time': current_time, 'type': 'ENTRY', 'side': 'LONG'})
                                    
                elif htf_t == Trend.BEARISH and ema20 < ema50 and mtf_t == Trend.BEARISH and ltf_t == Trend.BEARISH:
                    body = abs(c - o)
                    candle_range = max(0.01, h - l)
                    if (body / candle_range) >= 0.50 and v >= (vsma * 1.05) and c < o:
                        ltf_h = ltf_highs[i]
                        if ltf_h and ltf_h.price > c:
                            sl = ltf_h.price
                            risk_dist = sl - c
                            sl_pct = risk_dist / c
                            if min_sl <= sl_pct <= max_sl:
                                pos_sz, d_risk, eff_risk = self.vol_sizer.compute_volatility_adjusted_size(
                                    current_equity=capital,
                                    entry_price=c,
                                    sl_price=sl,
                                    current_atr=cur_atr,
                                    median_atr=median_atr
                                )
                                if pos_sz > 0 and self.governor.can_open_new_trade(asset, eff_risk, capital, current_date):
                                    tp = c - (risk_dist * 4.0)
                                    in_trade = True
                                    side = 'SHORT'
                                    entry_price = c
                                    sl_price = sl
                                    tp_price = tp
                                    partial_tp_price = c - (risk_dist * 2.0)
                                    position_size = pos_sz
                                    fee_entry = entry_price * position_size * self.taker_fee_pct
                                    capital -= fee_entry
                                    has_taken_partial = False
                                    trades.append({'time': current_time, 'type': 'ENTRY', 'side': 'SHORT'})
                                    
            daily_equity[current_date] = capital

        exits = [t for t in trades if t['type'] in ['SL_OR_BE', 'TP', 'EXIT_SL_OR_BE', 'EXIT_TP']]
        wins = [t for t in exits if t['pnl'] > 0]
        losses = [t for t in exits if t['pnl'] < 0]
        
        gross_p = sum(t['pnl'] for t in wins)
        gross_l = abs(sum(t['pnl'] for t in losses))
        pf = (gross_p / gross_l) if gross_l > 0 else (999.0 if gross_p > 0 else 0.0)
        
        total_exits = len(exits)
        win_rate = (len(wins) / total_exits) * 100 if total_exits > 0 else 0.0
        
        net_profit = capital - self.initial_capital
        net_roi = (net_profit / self.initial_capital) * 100
        
        daily_s = pd.Series(daily_equity)
        daily_returns = daily_s.pct_change().dropna()
        
        days = (pd.to_datetime(df_ltf.iloc[-1]['datetime']) - pd.to_datetime(df_ltf.iloc[0]['datetime'])).days
        years = max(0.1, days / 365.25)
        cagr = (((capital / self.initial_capital) ** (1.0 / years)) - 1.0) * 100.0 if capital > 0 else -100.0
        
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
            downside_returns = daily_returns[daily_returns < 0]
            downside_std = downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() > 0 else daily_returns.std()
            sortino = (daily_returns.mean() / downside_std) * np.sqrt(365)
        else:
            sharpe = 0.0
            sortino = 0.0
            
        return VolatilitySmoothedResult(
            asset=asset,
            set_name=set_name,
            htf_tf=htf_tf,
            mtf_tf=mtf_tf,
            ltf_tf=ltf_tf,
            start_date=str(df_ltf.iloc[0]['datetime'])[:10],
            end_date=str(df_ltf.iloc[-1]['datetime'])[:10],
            initial_capital=self.initial_capital,
            final_capital=capital,
            net_profit=net_profit,
            net_return_pct=net_roi,
            cagr_pct=cagr,
            max_drawdown_pct=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            total_trades=total_exits,
            wins_4r=len(wins),
            losses_1r=len(losses),
            win_rate=win_rate,
            profit_factor=pf
        )

    def run_full_matrix(self):
        print("=" * 115)
        print("🏛️  APEX QUANT OS: VOLATILITY-SMOOTHED INSTITUTIONAL MATRIX (ALL 12 CARTRIDGES)")
        print("   Equipped with Dynamic Inverse-ATR Risk Sizing + 2.5% Portfolio Heat Governor")
        print("=" * 115)
        
        master_t0 = time.time()
        results: List[VolatilitySmoothedResult] = []
        
        for asset in self.assets.keys():
            ds = self.load_and_downsample_asset(asset)
            print(f"\n[⚡ EXECUTING VOLATILITY-SMOOTHED SUITE] Asset: {asset}")
            print("─" * 115)
            for set_name, config in self.timeframe_sets.items():
                print(f"  ▶ [{set_name:<25}] (HTF:{config['htf']:<3} -> MTF:{config['mtf']:<3} -> LTF:{config['ltf']:<5})...", end="", flush=True)
                t_sub = time.time()
                perf = self.run_single_simulation(asset, set_name, config, ds)
                if perf:
                    results.append(perf)
                    print(f" Done ({time.time()-t_sub:4.2f}s) | Trades: {perf.total_trades:3d} | WR: {perf.win_rate:4.1f}% | Net ROI: {perf.net_return_pct:+7.1f}% | Sharpe: {perf.sharpe_ratio:4.2f} | MaxDD: {perf.max_drawdown_pct:4.1f}%")
                    
        # Summary Matrix Display
        print("\n" + "=" * 122)
        print("                      📊 VOLATILITY-SMOOTHED INSTITUTIONAL RISK MATRIX (12 CARTRIDGES)")
        print("=" * 122)
        print(f"{'Asset':<8} | {'Strategy Set':<25} | {'Trades':<6} | {'Win Rate':<8} | {'Profit Factor':<13} | {'Net Profit':<12} | {'Max DD%':<8} | {'Sharpe':<7} | {'Net ROI%':<9}")
        print("─" * 122)
        
        total_initial = 0.0
        total_final = 0.0
        total_trades = 0
        total_wins = 0
        
        for r in results:
            total_initial += r.initial_capital
            total_final += r.final_capital
            total_trades += r.total_trades
            total_wins += r.wins_4r
            print(f"{r.asset:<8} | {r.set_name:<25} | {r.total_trades:<6d} | {r.win_rate:>6.1f}%  | {r.profit_factor:>11.2f}  | ${r.net_profit:>+10.2f} | {r.max_drawdown_pct:>6.2f}% | {r.sharpe_ratio:>6.2f} | {r.net_return_pct:>+8.1f}%")
            
        print("─" * 122)
        total_fund_roi = ((total_final - total_initial) / total_initial) * 100
        fund_wr = (total_wins / total_trades) * 100 if total_trades > 0 else 0.0
        
        print("\n" + "=" * 90)
        print("🏆 CONSOLIDATED VOLATILITY-SMOOTHED FUND TEAR SHEET")
        print("=" * 90)
        print(f"Total Multi-Strategy Initial Capital: ${total_initial:,.2f}")
        print(f"Total Multi-Strategy Final Capital:   ${total_final:,.2f}")
        print(f"Consolidated Realized Net Profit:     ${(total_final - total_initial):+,.2f} ({total_fund_roi:+.2f}%)")
        print(f"Consolidated Portfolio Win Rate:      {fund_wr:.2f}%")
        print(f"Total System Trades Executed:         {total_trades:,}")
        print(f"Total Execution Runtime:              {time.time() - master_t0:.2f} seconds")
        print("=" * 90)

if __name__ == "__main__":
    matrix = InstitutionalVolatilityMasterMatrix(initial_capital_per_cartridge=10000.0)
    matrix.run_full_matrix()
