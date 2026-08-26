import sys
import os
import time
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core_vNext.structure.swing_engine import SwingEngine, Trend

def run_aggressive_10_dollar_simulation():
    filepath = "data/archives/SOLUSDT_final_compliance.csv"
    df = pd.read_csv(filepath, usecols=[0, 2, 3, 4, 5, 6], names=['datetime', 'open', 'high', 'low', 'close', 'volume'], header=0)
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    df = df.sort_values('datetime').set_index('datetime')
    
    # 1-year window
    df_1yr = df.loc['2025-06-01':'2026-06-01']
    
    ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    df_4h = df_1yr.resample('4h').agg(ohlc).dropna()
    df_1h = df_1yr.resample('1h').agg(ohlc).dropna()
    df_15m = df_1yr.resample('15min').agg(ohlc).dropna()
    
    df_4h['timestamp'] = df_4h.index.view('int64') // 10**6
    df_1h['timestamp'] = df_1h.index.view('int64') // 10**6
    df_15m['timestamp'] = df_15m.index.view('int64') // 10**6
    
    df_4h['ema20'] = df_4h['close'].ewm(span=20).mean()
    df_4h['ema50'] = df_4h['close'].ewm(span=50).mean()
    df_15m['vol_sma'] = df_15m['volume'].rolling(20).mean().fillna(df_15m['volume'])
    
    df_4h = df_4h.reset_index()
    df_1h = df_1h.reset_index()
    df_15m = df_15m.reset_index()
    
    swing_4h = SwingEngine(k=3)
    swing_1h = SwingEngine(k=3)
    swing_15m = SwingEngine(k=2)
    
    trends_4h = []
    for i in range(len(df_4h)):
        if i >= 3:
            swing_4h._evaluate_step(i, df_4h['timestamp'].values, df_4h['high'].values, df_4h['low'].values, df_4h['close'].values)
        trends_4h.append(swing_4h.current_trend)
        
    trends_1h = []
    for i in range(len(df_1h)):
        if i >= 3:
            swing_1h._evaluate_step(i, df_1h['timestamp'].values, df_1h['high'].values, df_1h['low'].values, df_1h['close'].values)
        trends_1h.append(swing_1h.current_trend)
        
    trends_15m = []
    highs_15m = []
    lows_15m = []
    for i in range(len(df_15m)):
        if i >= 2:
            swing_15m._evaluate_step(i, df_15m['timestamp'].values, df_15m['high'].values, df_15m['low'].values, df_15m['close'].values)
        trends_15m.append(swing_15m.current_trend)
        highs_15m.append(swing_15m.last_confirmed_high)
        lows_15m.append(swing_15m.last_confirmed_low)
        
    ts_4h = df_4h['datetime'].values
    ts_1h = df_1h['datetime'].values
    ts_15m = df_15m['datetime'].values
    
    idx_4h = np.searchsorted(ts_4h, ts_15m, side='right') - 1
    idx_1h = np.searchsorted(ts_1h, ts_15m, side='right') - 1
    
    print("=" * 80)
    print("⚡ AGGRESSIVE HIGH-LEVERAGE COMPOUNDING SIMULATION ($10 ACCOUNT)")
    print("   Comparing Risk Tiers: Conservative (2%) vs Moderate (5%) vs Aggressive (10%)")
    print("=" * 80)
    
    risk_tiers = [0.02, 0.05, 0.10]
    
    for risk_pct in risk_tiers:
        capital = 10.00
        initial_capital = capital
        peak_capital = capital
        max_dd = 0.0
        trades = []
        in_trade = False
        side = 'LONG'
        entry_p = 0.0
        sl_p = 0.0
        tp_p = 0.0
        partial_p = 0.0
        pos_size = 0.0
        has_partial = False
        
        taker_fee = 0.0004
        slippage = 0.0002
        
        closes = df_15m['close'].values
        highs = df_15m['high'].values
        lows = df_15m['low'].values
        opens = df_15m['open'].values
        volumes = df_15m['volume'].values
        vol_smas = df_15m['vol_sma'].values
        
        for i in range(15, len(df_15m)):
            c = closes[i]
            h = highs[i]
            l = lows[i]
            o = opens[i]
            v = volumes[i]
            vsma = vol_smas[i]
            
            i_4h = max(0, idx_4h[i])
            i_1h = max(0, idx_1h[i])
            
            t_4h = trends_4h[i_4h]
            t_1h = trends_1h[i_1h]
            t_15m = trends_15m[i]
            
            ema20 = df_4h['ema20'].values[i_4h]
            ema50 = df_4h['ema50'].values[i_4h]
            
            if in_trade:
                if not has_partial:
                    if side == 'LONG' and h >= partial_p:
                        realized = partial_p * (1.0 - slippage)
                        fee = realized * (pos_size * 0.5) * taker_fee
                        net = ((realized - entry_p) * (pos_size * 0.5)) - fee
                        capital += net
                        pos_size *= 0.5
                        sl_p = entry_p * 1.002
                        has_partial = True
                        trades.append({'pnl': net, 'type': 'PARTIAL'})
                    elif side == 'SHORT' and l <= partial_p:
                        realized = partial_p * (1.0 + slippage)
                        fee = realized * (pos_size * 0.5) * taker_fee
                        net = ((entry_p - realized) * (pos_size * 0.5)) - fee
                        capital += net
                        pos_size *= 0.5
                        sl_p = entry_p * 0.998
                        has_partial = True
                        trades.append({'pnl': net, 'type': 'PARTIAL'})
                        
                if side == 'LONG':
                    if l <= sl_p:
                        realized = sl_p * (1.0 - slippage)
                        fee = realized * pos_size * taker_fee
                        net = ((realized - entry_p) * pos_size) - fee
                        capital += net
                        in_trade = False
                        has_partial = False
                        trades.append({'pnl': net, 'type': 'SL'})
                    elif h >= tp_p:
                        realized = tp_p * (1.0 - slippage)
                        fee = realized * pos_size * taker_fee
                        net = ((realized - entry_p) * pos_size) - fee
                        capital += net
                        in_trade = False
                        has_partial = False
                        trades.append({'pnl': net, 'type': 'TP'})
                else:
                    if h >= sl_p:
                        realized = sl_p * (1.0 + slippage)
                        fee = realized * pos_size * taker_fee
                        net = ((entry_p - realized) * pos_size) - fee
                        capital += net
                        in_trade = False
                        has_partial = False
                        trades.append({'pnl': net, 'type': 'SL'})
                    elif l <= tp_p:
                        realized = tp_p * (1.0 + slippage)
                        fee = realized * pos_size * taker_fee
                        net = ((entry_p - realized) * pos_size) - fee
                        capital += net
                        in_trade = False
                        has_partial = False
                        trades.append({'pnl': net, 'type': 'TP'})
                        
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100
                if dd > max_dd:
                    max_dd = dd
                continue
                
            if not in_trade:
                if t_4h == Trend.BULLISH and ema20 > ema50 and t_1h == Trend.BULLISH and t_15m == Trend.BULLISH:
                    body = abs(c - o)
                    candle_range = max(0.01, h - l)
                    if (body / candle_range) >= 0.50 and v >= (vsma * 1.05) and c > o:
                        ltf_l = lows_15m[i]
                        if ltf_l and ltf_l.price < c:
                            sl = ltf_l.price
                            risk_dist = c - sl
                            sl_pct = risk_dist / c
                            if 0.006 <= sl_pct <= 0.035:
                                tp = c + (risk_dist * 4.0)
                                in_trade = True
                                side = 'LONG'
                                entry_p = c
                                sl_p = sl
                                tp_p = tp
                                partial_p = c + (risk_dist * 2.0)
                                # Sizing based on risk tier
                                pos_size = (capital * risk_pct) / risk_dist
                                fee_entry = entry_p * pos_size * taker_fee
                                capital -= fee_entry
                                has_partial = False
                                
                elif t_4h == Trend.BEARISH and ema20 < ema50 and t_1h == Trend.BEARISH and t_15m == Trend.BEARISH:
                    body = abs(c - o)
                    candle_range = max(0.01, h - l)
                    if (body / candle_range) >= 0.50 and v >= (vsma * 1.05) and c < o:
                        ltf_h = highs_15m[i]
                        if ltf_h and ltf_h.price > c:
                            sl = ltf_h.price
                            risk_dist = sl - c
                            sl_pct = risk_dist / c
                            if 0.006 <= sl_pct <= 0.035:
                                tp = c - (risk_dist * 4.0)
                                in_trade = True
                                side = 'SHORT'
                                entry_p = c
                                sl_p = sl
                                tp_p = tp
                                partial_p = c - (risk_dist * 2.0)
                                pos_size = (capital * risk_pct) / risk_dist
                                fee_entry = entry_p * pos_size * taker_fee
                                capital -= fee_entry
                                has_partial = False

        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        roi = ((capital - initial_capital) / initial_capital) * 100
        print(f"Risk Tier: {risk_pct*100:4.1f}% per trade | $10.00 -> ${capital:>9.2f} ({roi:>+8.2f}%) | Max DD: {max_dd:5.1f}% | Trades: {len(wins)+len(losses)}")

if __name__ == '__main__':
    run_aggressive_10_dollar_simulation()
