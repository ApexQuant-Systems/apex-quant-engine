import sys
import os
import time
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core_vNext.structure.swing_engine import SwingEngine, Trend

def run_1year_12cartridge_simulation():
    assets = {
        "BTCUSDT": "data/archives/BTCUSDT_final_compliance.csv",
        "ETHUSDT": "data/archives/ETHUSDT_final_compliance.csv",
        "SOLUSDT": "data/archives/SOLUSDT_final_compliance.csv"
    }
    
    timeframe_sets = {
        "SET_1_MACRO_INVESTING":     {"htf": "1ME", "mtf": "1W",  "ltf": "1D",    "min_sl": 0.015, "max_sl": 0.200},
        "SET_2_MEDIUM_SWING":        {"htf": "1W",  "mtf": "1D",  "ltf": "4h",    "min_sl": 0.012, "max_sl": 0.100},
        "SET_3_POSITION_PLAY":        {"htf": "1D",  "mtf": "4h",  "ltf": "1h",    "min_sl": 0.008, "max_sl": 0.050},
        "SET_4_INTRADAY_EXPANSION":   {"htf": "4h",  "mtf": "1h",  "ltf": "15min", "min_sl": 0.006, "max_sl": 0.035}
    }
    
    print("=" * 105)
    print("🧪 1-YEAR FULL MULTI-STRATEGY AUTOMATION TEST: $10 ACCOUNT")
    print("   Running ALL 3 Assets × ALL 4 Timeframe Sets (12 Concurrent Cartridges)")
    print("   Testing 1-Year Period: June 1, 2025 -> June 1, 2026 (100% Fees & Slippage Deducted)")
    print("=" * 105)
    
    results = []
    
    taker_fee = 0.0004  # 0.04%
    slippage = 0.0002   # 0.02%
    
    for asset, filepath in assets.items():
        df = pd.read_csv(filepath, usecols=[0, 2, 3, 4, 5, 6], names=['datetime', 'open', 'high', 'low', 'close', 'volume'], header=0)
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        df = df.sort_values('datetime').set_index('datetime')
        
        # 1-year window
        df_1yr = df.loc['2025-06-01':'2026-06-01']
        
        ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        
        ds = {
            "15min": df_1yr.resample('15min').agg(ohlc).dropna(),
            "1h":    df_1yr.resample('1h').agg(ohlc).dropna(),
            "4h":    df_1yr.resample('4h').agg(ohlc).dropna(),
            "1D":    df_1yr.resample('1D').agg(ohlc).dropna(),
            "1W":    df_1yr.resample('1W').agg(ohlc).dropna(),
            "1ME":   df_1yr.resample('1ME').agg(ohlc).dropna()
        }
        
        for tf, frame in ds.items():
            frame['timestamp'] = frame.index.view('int64') // 10**6
            frame['vol_sma'] = frame['volume'].rolling(20).mean().fillna(frame['volume'])
            frame['ema20'] = frame['close'].ewm(span=20).mean()
            frame['ema50'] = frame['close'].ewm(span=50).mean()
            ds[tf] = frame.reset_index()
            
        swings = {}
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
            swings[tf] = (trends, last_highs, last_lows)
            
        for set_name, config in timeframe_sets.items():
            htf_tf = config['htf']
            mtf_tf = config['mtf']
            ltf_tf = config['ltf']
            min_sl = config['min_sl']
            max_sl = config['max_sl']
            
            df_htf = ds[htf_tf]
            df_mtf = ds[mtf_tf]
            df_ltf = ds[ltf_tf]
            
            htf_trends, _, _ = swings[htf_tf]
            mtf_trends, _, _ = swings[mtf_tf]
            ltf_trends, ltf_highs, ltf_lows = swings[ltf_tf]
            
            htf_ema20 = df_htf['ema20'].values
            htf_ema50 = df_htf['ema50'].values
            
            if len(df_ltf) < 20:
                continue
                
            htf_ts = df_htf['datetime'].values
            mtf_ts = df_mtf['datetime'].values
            ltf_ts = df_ltf['datetime'].values
            
            htf_idx_map = np.searchsorted(htf_ts, ltf_ts, side='right') - 1
            mtf_idx_map = np.searchsorted(mtf_ts, ltf_ts, side='right') - 1
            
            # Start each cartridge with $10
            capital = 10.00
            initial_capital = capital
            peak_capital = capital
            max_dd = 0.0
            
            trades = []
            in_trade = False
            side = 'LONG'
            entry_price = 0.0
            sl_price = 0.0
            tp_price = 0.0
            partial_tp_price = 0.0
            position_size = 0.0
            has_taken_partial = False
            
            closes = df_ltf['close'].values
            highs = df_ltf['high'].values
            lows = df_ltf['low'].values
            opens = df_ltf['open'].values
            volumes = df_ltf['volume'].values
            vol_smas = df_ltf['vol_sma'].values
            
            for i in range(15, len(df_ltf)):
                c = closes[i]
                h = highs[i]
                l = lows[i]
                o = opens[i]
                v = volumes[i]
                vsma = vol_smas[i]
                
                h_idx = max(0, htf_idx_map[i])
                m_idx = max(0, mtf_idx_map[i])
                
                htf_t = htf_trends[h_idx]
                mtf_t = mtf_trends[m_idx]
                ltf_t = ltf_trends[i]
                
                ema20 = htf_ema20[h_idx]
                ema50 = htf_ema50[h_idx]
                
                # Trade management
                if in_trade:
                    if not has_taken_partial:
                        if side == 'LONG' and h >= partial_tp_price:
                            realized = partial_tp_price * (1.0 - slippage)
                            fee = realized * (position_size * 0.5) * taker_fee
                            net = ((realized - entry_price) * (position_size * 0.5)) - fee
                            capital += net
                            position_size *= 0.5
                            sl_price = entry_price * 1.002
                            has_taken_partial = True
                            trades.append({'pnl': net, 'type': 'PARTIAL'})
                        elif side == 'SHORT' and l <= partial_tp_price:
                            realized = partial_tp_price * (1.0 + slippage)
                            fee = realized * (position_size * 0.5) * taker_fee
                            net = ((entry_price - realized) * (position_size * 0.5)) - fee
                            capital += net
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
                            in_trade = False
                            has_taken_partial = False
                            trades.append({'pnl': net, 'type': 'SL_OR_BE'})
                        elif h >= tp_price:
                            realized = tp_price * (1.0 - slippage)
                            fee = realized * position_size * taker_fee
                            net = ((realized - entry_price) * position_size) - fee
                            capital += net
                            in_trade = False
                            has_taken_partial = False
                            trades.append({'pnl': net, 'type': 'TP'})
                    else:
                        if h >= sl_price:
                            realized = sl_price * (1.0 + slippage)
                            fee = realized * position_size * taker_fee
                            net = ((entry_price - realized) * position_size) - fee
                            capital += net
                            in_trade = False
                            has_taken_partial = False
                            trades.append({'pnl': net, 'type': 'SL_OR_BE'})
                        elif l <= tp_price:
                            realized = tp_price * (1.0 + slippage)
                            fee = realized * position_size * taker_fee
                            net = ((entry_price - realized) * position_size) - fee
                            capital += net
                            in_trade = False
                            has_taken_partial = False
                            trades.append({'pnl': net, 'type': 'TP'})
                            
                    if capital > peak_capital:
                        peak_capital = capital
                    dd = (peak_capital - capital) / peak_capital * 100
                    if dd > max_dd:
                        max_dd = dd
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
                                    tp = c + (risk_dist * 4.0)
                                    in_trade = True
                                    side = 'LONG'
                                    entry_price = c
                                    sl_price = sl
                                    tp_price = tp
                                    partial_tp_price = c + (risk_dist * 2.0)
                                    position_size = (capital * 0.02) / risk_dist
                                    fee_entry = entry_price * position_size * taker_fee
                                    capital -= fee_entry
                                    has_taken_partial = False
                                    
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
                                    has_taken_partial = False

            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] < 0]
            total_t = len(wins) + len(losses)
            wr = (len(wins) / total_t * 100) if total_t > 0 else 0
            net_pnl = capital - initial_capital
            roi = (net_pnl / initial_capital) * 100
            
            results.append({
                "asset": asset,
                "set": set_name,
                "start": initial_capital,
                "end": capital,
                "net_pnl": net_pnl,
                "roi": roi,
                "trades": total_t,
                "win_rate": wr,
                "max_dd": max_dd
            })
            
    print("\n" + "=" * 105)
    print("                     📊 1-YEAR $10 ACCOUNT PERFORMANCE MATRIX (ALL 12 CARTRIDGES)")
    print("=" * 105)
    print(f"{'Asset':<8} | {'Strategy Set':<25} | {'Starting $':<11} | {'Ending $':<11} | {'1-Yr ROI %':<11} | {'Trades':<8} | {'Win Rate':<9}")
    print("─" * 105)
    
    total_start_fund = 0.0
    total_end_fund = 0.0
    total_trades = 0
    
    for r in results:
        total_start_fund += r['start']
        total_end_fund += r['end']
        total_trades += r['trades']
        print(f"{r['asset']:<8} | {r['set']:<25} | ${r['start']:>8.2f}   | ${r['end']:>8.2f}   | {r['roi']:>+8.2f}%   | {r['trades']:<8d} | {r['win_rate']:>6.1f}%")
        
    print("─" * 105)
    total_fund_roi = ((total_end_fund - total_start_fund) / total_start_fund) * 100
    
    # Calculate what a single $10 account split equally across the 12 cartridges becomes
    single_10_end = 10.0 * (1.0 + (total_fund_roi / 100.0))
    
    print("\n" + "=" * 80)
    print("🏆 FINAL VERDICT: LEAVING A $10 ACCOUNT FULLY AUTOMATED FOR 1 YEAR")
    print("=" * 80)
    print(f"• If you allocate $10 equally across the entire 12-strategy portfolio:")
    print(f"  Starting Balance:  $10.00")
    print(f"  Ending Balance:    ${single_10_end:.2f}")
    print(f"  Net Real Profit:   ${(single_10_end - 10.00):+,.2f} ({total_fund_roi:+.2f}% NET ROI)")
    print(f"  Total Trades Run:  {total_trades:,} automated executions")
    print("=" * 80)

if __name__ == '__main__':
    run_1year_12cartridge_simulation()
