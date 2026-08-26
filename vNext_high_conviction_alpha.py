import sys
import os
import time
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core_vNext.structure.swing_engine import SwingEngine, Trend

@dataclass
class HighConvictionResult:
    asset: str
    initial_cap: float
    final_cap: float
    net_profit: float
    net_roi_pct: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    max_dd: float
    profit_factor: float
    sharpe: float

def run_asset_test(asset: str, filepath: str) -> HighConvictionResult:
    print(f"\n[🚀 EVALUATING ASSET] {asset} -> {filepath}...")
    t0 = time.time()
    df = pd.read_csv(filepath, usecols=[0, 2, 3, 4, 5, 6], names=['datetime', 'open', 'high', 'low', 'close', 'volume'], header=0)
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    df = df.sort_values('datetime').set_index('datetime')
    
    ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    
    # Macro=1D, Intermediate=4H, Trigger=1H
    df_1d = df.resample('1D').agg(ohlc).dropna()
    df_4h = df.resample('4h').agg(ohlc).dropna()
    df_1h = df.resample('1h').agg(ohlc).dropna()
    
    df_1d['timestamp'] = df_1d.index.view('int64') // 10**6
    df_4h['timestamp'] = df_4h.index.view('int64') // 10**6
    df_1h['timestamp'] = df_1h.index.view('int64') // 10**6
    
    df_1d = df_1d.reset_index()
    df_4h = df_4h.reset_index()
    df_1h = df_1h.reset_index()
    
    # 20 EMA & 50 EMA on 1D
    df_1d['ema20'] = df_1d['close'].ewm(span=20).mean()
    df_1d['ema50'] = df_1d['close'].ewm(span=50).mean()
    df_1h['vol_sma'] = df_1h['volume'].rolling(20).mean().fillna(df_1h['volume'])
    
    swing_1d = SwingEngine(k=3)
    swing_4h = SwingEngine(k=3)
    swing_1h = SwingEngine(k=2)
    
    trends_1d = []
    for i in range(len(df_1d)):
        if i >= 3:
            swing_1d._evaluate_step(i, df_1d['timestamp'].values, df_1d['high'].values, df_1d['low'].values, df_1d['close'].values)
        trends_1d.append(swing_1d.current_trend)
        
    trends_4h = []
    for i in range(len(df_4h)):
        if i >= 3:
            swing_4h._evaluate_step(i, df_4h['timestamp'].values, df_4h['high'].values, df_4h['low'].values, df_4h['close'].values)
        trends_4h.append(swing_4h.current_trend)
        
    trends_1h = []
    highs_1h = []
    lows_1h = []
    for i in range(len(df_1h)):
        if i >= 2:
            swing_1h._evaluate_step(i, df_1h['timestamp'].values, df_1h['high'].values, df_1h['low'].values, df_1h['close'].values)
        trends_1h.append(swing_1h.current_trend)
        highs_1h.append(swing_1h.last_confirmed_high)
        lows_1h.append(swing_1h.last_confirmed_low)
        
    ts_1d = df_1d['datetime'].values
    ts_4h = df_4h['datetime'].values
    ts_1h = df_1h['datetime'].values
    
    idx_1d = np.searchsorted(ts_1d, ts_1h, side='right') - 1
    idx_4h = np.searchsorted(ts_4h, ts_1h, side='right') - 1
    
    capital = 10000.0
    initial_capital = capital
    peak_capital = capital
    max_dd = 0.0
    daily_equity = {}
    
    trades = []
    in_trade = False
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    partial_p = 0.0
    pos_size = 0.0
    has_partial = False
    side = 'LONG'
    
    taker_fee = 0.0004 # 0.04%
    slippage = 0.0002 # 0.02%
    
    closes = df_1h['close'].values
    highs = df_1h['high'].values
    lows = df_1h['low'].values
    opens = df_1h['open'].values
    volumes = df_1h['volume'].values
    vol_smas = df_1h['vol_sma'].values
    datetimes = df_1h['datetime'].values
    
    for i in range(50, len(df_1h)):
        current_date = str(datetimes[i])[:10]
        i_1d = max(0, idx_1d[i])
        i_4h = max(0, idx_4h[i])
        
        c = closes[i]
        h = highs[i]
        l = lows[i]
        o = opens[i]
        v = volumes[i]
        vsma = vol_smas[i]
        
        t_1d = trends_1d[i_1d]
        t_4h = trends_4h[i_4h]
        t_1h = trends_1h[i]
        
        ema20 = df_1d['ema20'].values[i_1d]
        ema50 = df_1d['ema50'].values[i_1d]
        
        if in_trade:
            if not has_partial:
                if side == 'LONG' and h >= partial_p:
                    realized = partial_p * (1 - slippage)
                    fee = realized * (pos_size * 0.5) * taker_fee
                    net = (realized - entry_p) * (pos_size * 0.5) - fee
                    capital += net
                    pos_size *= 0.5
                    sl_p = entry_p * 1.002
                    has_partial = True
                    trades.append({'pnl': net, 'type': 'PARTIAL'})
                elif side == 'SHORT' and l <= partial_p:
                    realized = partial_p * (1 + slippage)
                    fee = realized * (pos_size * 0.5) * taker_fee
                    net = (entry_p - realized) * (pos_size * 0.5) - fee
                    capital += net
                    pos_size *= 0.5
                    sl_p = entry_p * 0.998
                    has_partial = True
                    trades.append({'pnl': net, 'type': 'PARTIAL'})
                    
            if side == 'LONG':
                if l <= sl_p:
                    realized = sl_p * (1 - slippage)
                    fee = realized * pos_size * taker_fee
                    net = (realized - entry_p) * pos_size - fee
                    capital += net
                    in_trade = False
                    has_partial = False
                    trades.append({'pnl': net, 'type': 'SL'})
                elif h >= tp_p:
                    realized = tp_p * (1 - slippage)
                    fee = realized * pos_size * taker_fee
                    net = (realized - entry_p) * pos_size - fee
                    capital += net
                    in_trade = False
                    has_partial = False
                    trades.append({'pnl': net, 'type': 'TP'})
            else:
                if h >= sl_p:
                    realized = sl_p * (1 + slippage)
                    fee = realized * pos_size * taker_fee
                    net = (entry_p - realized) * pos_size - fee
                    capital += net
                    in_trade = False
                    has_partial = False
                    trades.append({'pnl': net, 'type': 'SL'})
                elif l <= tp_p:
                    realized = tp_p * (1 + slippage)
                    fee = realized * pos_size * taker_fee
                    net = (entry_p - realized) * pos_size - fee
                    capital += net
                    in_trade = False
                    has_partial = False
                    trades.append({'pnl': net, 'type': 'TP'})
                    
            if capital > peak_capital:
                peak_capital = capital
            dd = (peak_capital - capital) / peak_capital * 100
            if dd > max_dd:
                max_dd = dd
            daily_equity[current_date] = capital
            continue
            
        # High Conviction Entry
        if not in_trade:
            if t_1d == Trend.BULLISH and ema20 > ema50 and t_4h == Trend.BULLISH and t_1h == Trend.BULLISH:
                body = abs(c - o)
                candle_range = max(0.01, h - l)
                if (body / candle_range) >= 0.55 and v > (vsma * 1.1) and c > o:
                    l_1h = lows_1h[i]
                    if l_1h and l_1h.price < c:
                        sl = l_1h.price
                        risk_dist = c - sl
                        sl_pct = risk_dist / c
                        if 0.010 <= sl_pct <= 0.050:
                            tp = c + (risk_dist * 4.0)
                            in_trade = True
                            side = 'LONG'
                            entry_p = c
                            sl_p = sl
                            tp_p = tp
                            partial_p = c + (risk_dist * 2.0)
                            pos_size = (capital * 0.015) / risk_dist # 1.5% Risk per trade
                            fee_entry = entry_p * pos_size * taker_fee
                            capital -= fee_entry
                            has_partial = False
                            
            elif t_1d == Trend.BEARISH and ema20 < ema50 and t_4h == Trend.BEARISH and t_1h == Trend.BEARISH:
                body = abs(c - o)
                candle_range = max(0.01, h - l)
                if (body / candle_range) >= 0.55 and v > (vsma * 1.1) and c < o:
                    h_1h = highs_1h[i]
                    if h_1h and h_1h.price > c:
                        sl = h_1h.price
                        risk_dist = sl - c
                        sl_pct = risk_dist / c
                        if 0.010 <= sl_pct <= 0.050:
                            tp = c - (risk_dist * 4.0)
                            in_trade = True
                            side = 'SHORT'
                            entry_p = c
                            sl_p = sl
                            tp_p = tp
                            partial_p = c - (risk_dist * 2.0)
                            pos_size = (capital * 0.015) / risk_dist
                            fee_entry = entry_p * pos_size * taker_fee
                            capital -= fee_entry
                            has_partial = False
                            
        daily_equity[current_date] = capital

    net_profit = capital - initial_capital
    roi = (net_profit / initial_capital) * 100
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    total_trades = len(wins) + len(losses)
    wr = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    gross_p = sum(t['pnl'] for t in wins)
    gross_l = abs(sum(t['pnl'] for t in losses))
    pf = gross_p / gross_l if gross_l > 0 else 999.0
    
    daily_s = pd.Series(daily_equity)
    daily_ret = daily_s.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std()) * np.sqrt(365) if len(daily_ret) > 1 and daily_ret.std() > 0 else 0.0
    
    return HighConvictionResult(
        asset=asset,
        initial_cap=initial_capital,
        final_cap=capital,
        net_profit=net_profit,
        net_roi_pct=roi,
        total_trades=total_trades,
        wins=len(wins),
        losses=len(losses),
        win_rate=wr,
        max_dd=max_dd,
        profit_factor=pf,
        sharpe=sharpe
    )

def main():
    assets = {
        "BTCUSDT": "data/archives/BTCUSDT_final_compliance.csv",
        "ETHUSDT": "data/archives/ETHUSDT_final_compliance.csv",
        "SOLUSDT": "data/archives/SOLUSDT_final_compliance.csv"
    }
    
    print("=" * 95)
    print("🏛️  APEX QUANT OS: HIGH-CONVICTION MULTI-ASSET ALPHA PORTFOLIO")
    print("   100% Real Friction Injected: 0.04% Taker Fee + 0.02% Slippage on EVERY Trade")
    print("=" * 95)
    
    results = []
    for asset, path in assets.items():
        res = run_asset_test(asset, path)
        results.append(res)
        
    print("\n" + "=" * 95)
    print("                             📊 FINAL REAL-WORLD NET ALPHA TEAR SHEET")
    print("=" * 95)
    print(f"{'Asset':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Profit Factor':<15} | {'Max DD%':<10} | {'Sharpe':<8} | {'Net ROI %':<12}")
    print("─" * 95)
    
    total_init = 0.0
    total_final = 0.0
    total_trades = 0
    total_wins = 0
    
    for r in results:
        total_init += r.initial_cap
        total_final += r.final_cap
        total_trades += r.total_trades
        total_wins += r.wins
        print(f"{r.asset:<10} | {r.total_trades:<8d} | {r.win_rate:>8.2f}%  | {r.profit_factor:>13.2f}  | {r.max_dd:>8.2f}% | {r.sharpe:>6.2f} | {r.net_roi_pct:>+10.2f}%")
        
    print("─" * 95)
    tot_roi = ((total_final - total_init) / total_init) * 100
    tot_wr = (total_wins / total_trades) * 100 if total_trades > 0 else 0
    
    print("\n" + "=" * 65)
    print("🏆 CONSOLIDATED HIGH-CONVICTION FUND METRICS")
    print("=" * 65)
    print(f"Total Initial Portfolio:  ${total_init:,.2f}")
    print(f"Total Final Portfolio:    ${total_final:,.2f}")
    print(f"Total Realized Net Alpha: ${(total_final - total_init):+,.2f} ({tot_roi:+.2f}%)")
    print(f"Consolidated Win Rate:    {tot_wr:.2f}%")
    print(f"Total Trades Taken:       {total_trades}")
    print("=" * 65)

if __name__ == '__main__':
    main()
