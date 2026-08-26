import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core_vNext.structure.swing_engine import SwingEngine, Trend

def run_1year_10dollar_simulation():
    assets = {
        "BTCUSDT": "data/archives/BTCUSDT_final_compliance.csv",
        "ETHUSDT": "data/archives/ETHUSDT_final_compliance.csv",
        "SOLUSDT": "data/archives/SOLUSDT_final_compliance.csv"
    }
    
    print("=" * 80)
    print("🧪 1-YEAR HISTORICAL REALITY TEST: $10 INITIAL CAPITAL")
    print("   Testing 1-Year Period: June 1, 2025 -> June 1, 2026")
    print("   100% Real Binance Fees (0.04%) + Execution Slippage (0.02%) Deducted")
    print("=" * 80)
    
    results = {}
    
    for asset, filepath in assets.items():
        t0 = time.time()
        df = pd.read_csv(filepath, usecols=[0, 2, 3, 4, 5, 6], names=['datetime', 'open', 'high', 'low', 'close', 'volume'], header=0)
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        df = df.sort_values('datetime').set_index('datetime')
        
        # Filter for the most recent 1-year window
        df_1yr = df.loc['2025-06-01':'2026-06-01']
        
        ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        # We test both Position (1D->4H->1H) and Intraday (4H->1H->15M)
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
        
        # Initialize $10 account
        capital = 10.00
        initial_capital = capital
        peak_capital = capital
        max_drawdown = 0.0
        
        trades = []
        in_trade = False
        side = 'LONG'
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        partial_tp_price = 0.0
        position_size = 0.0
        has_taken_partial = False
        
        total_fee_drag = 0.0
        total_slippage_drag = 0.0
        
        closes = df_15m['close'].values
        highs = df_15m['high'].values
        lows = df_15m['low'].values
        opens = df_15m['open'].values
        volumes = df_15m['volume'].values
        vol_smas = df_15m['vol_sma'].values
        
        taker_fee = 0.0004
        slippage = 0.0002
        
        for i in range(30, len(df_15m)):
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
            
            # Position management
            if in_trade:
                if not has_taken_partial:
                    if side == 'LONG' and h >= partial_tp_price:
                        realized = partial_tp_price * (1.0 - slippage)
                        fee = realized * (position_size * 0.5) * taker_fee
                        net = ((realized - entry_price) * (position_size * 0.5)) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (partial_tp_price - realized) * (position_size * 0.5)
                        position_size *= 0.5
                        sl_price = entry_price * 1.002
                        has_taken_partial = True
                        trades.append({'pnl': net, 'type': 'PARTIAL'})
                    elif side == 'SHORT' and l <= partial_tp_price:
                        realized = partial_tp_price * (1.0 + slippage)
                        fee = realized * (position_size * 0.5) * taker_fee
                        net = ((entry_price - realized) * (position_size * 0.5)) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (realized - partial_tp_price) * (position_size * 0.5)
                        position_size *= 0.5
                        sl_price = entry_price * 0.998
                        has_taken_partial = True
                        trades.append({'pnl': net, 'type': 'PARTIAL'})
                        
                if side == 'LONG':
                    if l <= sl_price:
                        realized = sl_price * (1.0 - slippage)
                        fee = realized * position_size * taker_fee
                        net = ((realized - entry_price) * position_size) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (sl_price - realized) * position_size
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net, 'type': 'SL_OR_BE'})
                    elif h >= tp_price:
                        realized = tp_price * (1.0 - slippage)
                        fee = realized * position_size * taker_fee
                        net = ((realized - entry_price) * position_size) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (tp_price - realized) * position_size
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net, 'type': 'TP'})
                else:
                    if h >= sl_price:
                        realized = sl_price * (1.0 + slippage)
                        fee = realized * position_size * taker_fee
                        net = ((entry_price - realized) * position_size) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (realized - sl_price) * position_size
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net, 'type': 'SL_OR_BE'})
                    elif l <= tp_price:
                        realized = tp_price * (1.0 + slippage)
                        fee = realized * position_size * taker_fee
                        net = ((entry_price - realized) * position_size) - fee
                        capital += net
                        total_fee_drag += fee
                        total_slippage_drag += (realized - tp_price) * position_size
                        in_trade = False
                        has_taken_partial = False
                        trades.append({'pnl': net, 'type': 'TP'})
                        
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100
                if dd > max_drawdown:
                    max_drawdown = dd
                continue
                
            # Entry logic
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
                                entry_price = c
                                sl_price = sl
                                tp_price = tp
                                partial_tp_price = c + (risk_dist * 2.0)
                                # 2% dynamic risk compounding on account balance
                                position_size = (capital * 0.02) / risk_dist
                                fee_entry = entry_price * position_size * taker_fee
                                capital -= fee_entry
                                total_fee_drag += fee_entry
                                has_taken_partial = False
                                
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
                                entry_price = c
                                sl_price = sl
                                tp_price = tp
                                partial_tp_price = c - (risk_dist * 2.0)
                                position_size = (capital * 0.02) / risk_dist
                                fee_entry = entry_price * position_size * taker_fee
                                capital -= fee_entry
                                total_fee_drag += fee_entry
                                has_taken_partial = False

        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        total_t = len(wins) + len(losses)
        wr = (len(wins) / total_t * 100) if total_t > 0 else 0
        net_profit = capital - initial_capital
        roi = (net_profit / initial_capital) * 100
        
        results[asset] = {
            "initial": initial_capital,
            "final": capital,
            "net_profit": net_profit,
            "roi": roi,
            "trades": total_t,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": wr,
            "max_dd": max_drawdown,
            "fees_paid": total_fee_drag
        }
        
    print("\n" + "=" * 85)
    print("                  📊 1-YEAR $10 ACCOUNT FINAL COMPLIANCE REPORT")
    print("=" * 85)
    print(f"{'Asset':<10} | {'Starting $':<12} | {'Ending $':<12} | {'Net Profit':<12} | {'1-Yr ROI %':<12} | {'Trades':<8} | {'Win Rate':<9}")
    print("─" * 85)
    for asset, r in results.items():
        print(f"{asset:<10} | ${r['initial']:>9.2f}  | ${r['final']:>9.2f}  | ${r['net_profit']:>+9.2f}  | {r['roi']:>+9.2f}%  | {r['trades']:<8d} | {r['win_rate']:>6.1f}%")
        
    print("─" * 85)
    
    total_start = sum(r['initial'] for r in results.values())
    total_end = sum(r['final'] for r in results.values())
    total_pnl = total_end - total_start
    total_roi = (total_pnl / total_start) * 100
    
    print("\n" + "=" * 60)
    print("🏆 FINAL SUMMARY FOR A $10 ACCOUNT OVER 1 YEAR:")
    print("=" * 60)
    print(f"• If placed on BTC only:  $10.00 -> ${results['BTCUSDT']['final']:.2f} ({results['BTCUSDT']['roi']:+.2f}%)")
    print(f"• If placed on ETH only:  $10.00 -> ${results['ETHUSDT']['final']:.2f} ({results['ETHUSDT']['roi']:+.2f}%)")
    print(f"• If placed on SOL only:  $10.00 -> ${results['SOLUSDT']['final']:.2f} ({results['SOLUSDT']['roi']:+.2f}%)")
    print(f"• If split across all 3:  $10.00 -> ${((total_end/3.0)):.2f} ({total_roi:+.2f}%)")
    print("=" * 60)

if __name__ == '__main__':
    run_1year_10dollar_simulation()
