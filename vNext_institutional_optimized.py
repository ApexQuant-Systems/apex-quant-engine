import sys
import os
import time
import pandas as pd
import numpy as np
import pandas_ta as ta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core_vNext.structure.swing_engine import SwingEngine, Trend, SwingType, StructuralSwing
from core_vNext.structure.keyzone_engine import KeyzoneEngine, KeyzoneType, Keyzone
from core_vNext.strategy.strategy_state_machine import StrategyState
from core_vNext.execution.order_intent import OrderIntent, OrderSide
from core_vNext.risk.risk_guardian import RiskGuardian

@dataclass
class OptimizedInstitutionalPerf:
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
    total_fee_drag: float
    total_slippage_drag: float
    net_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_trades: int
    wins_4r: int
    losses_1r: int
    break_evens: int
    partials_2r: int
    win_rate_non_loss: float
    profit_factor: float
    mc_95_max_dd: float

class FastHorizonEngine:
    def __init__(self, df: pd.DataFrame, k: int = 3, mitigation_mode: str = 'touch'):
        self.df = df
        self.k = k
        self.mitigation_mode = mitigation_mode
        self.n = len(df)
        
        self.trends = [Trend.NEUTRAL] * self.n
        self.last_highs: List[Optional[StructuralSwing]] = [None] * self.n
        self.last_lows: List[Optional[StructuralSwing]] = [None] * self.n
        self.active_zones: List[List[Keyzone]] = [[] for _ in range(self.n)]
        
        self._precompute()

    def _precompute(self):
        swing_engine = SwingEngine(k=self.k)
        keyzone_engine = KeyzoneEngine(mitigation_mode=self.mitigation_mode)
        
        highs = self.df['high'].values
        lows = self.df['low'].values
        closes = self.df['close'].values
        timestamps = self.df['timestamp'].values
        
        for i in range(self.n):
            if i >= self.k:
                swing_engine._evaluate_step(i, timestamps, highs, lows, closes)
            if i >= 2:
                keyzone_engine._evaluate_step(i, timestamps, highs, lows)
                
            self.trends[i] = swing_engine.current_trend
            self.last_highs[i] = swing_engine.last_confirmed_high
            self.last_lows[i] = swing_engine.last_confirmed_low
            self.active_zones[i] = list(keyzone_engine.active_zones)

class OptimizedInstitutionalMatrix:
    def __init__(self, initial_capital_per_cartridge: float = 10000.0):
        self.initial_capital = initial_capital_per_cartridge
        # Realistic VIP / Pro Tier Maker/Taker blended rate: 0.02% (limit entries) - 0.04% (market exits)
        self.maker_entry_fee = 0.0002
        self.taker_exit_fee = 0.0004
        self.base_slippage = 0.00015 # 1.5 bps
        
        self.assets = {
            "BTCUSDT": "data/archives/BTCUSDT_final_compliance.csv",
            "ETHUSDT": "data/archives/ETHUSDT_final_compliance.csv",
            "SOLUSDT": "data/archives/SOLUSDT_final_compliance.csv"
        }
        
        self.timeframe_sets = {
            "SET_1_MACRO_INVESTING": {"htf": "1ME", "mtf": "1W", "ltf": "1D", "htf_k": 3, "mtf_k": 3, "ltf_k": 2},
            "SET_2_MEDIUM_SWING":    {"htf": "1W",  "mtf": "1D", "ltf": "4h", "htf_k": 3, "mtf_k": 3, "ltf_k": 2},
            "SET_3_POSITION_PLAY":    {"htf": "1D",  "mtf": "4h", "ltf": "1h", "htf_k": 3, "mtf_k": 3, "ltf_k": 2},
            "SET_4_INTRADAY_EXPANSION":{"htf": "4h",  "mtf": "1h", "ltf": "15min", "htf_k": 3, "mtf_k": 3, "ltf_k": 2}
        }
        
        self.cached_downsamples: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.cached_engines: Dict[str, Dict[str, FastHorizonEngine]] = {}
        self.cached_adx: Dict[str, Dict[str, np.ndarray]] = {}
        self.cached_atr: Dict[str, Dict[str, np.ndarray]] = {}

    def load_and_downsample_asset(self, asset: str):
        if asset in self.cached_downsamples:
            return self.cached_downsamples[asset]
            
        filepath = self.assets[asset]
        print(f"\n[📥 INGESTING REAL ARCHIVE] {asset} -> {filepath}...")
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
        
        for tf, frame in ds.items():
            frame['timestamp'] = frame.index.view('int64') // 10**6
            ds[tf] = frame.reset_index()
            
        self.cached_engines[asset] = {}
        self.cached_adx[asset] = {}
        self.cached_atr[asset] = {}
        
        for tf, frame in ds.items():
            k = 2 if tf == '15min' else 3
            mitigation = 'full_overlap' if tf in ['1ME', '1W'] else 'touch'
            self.cached_engines[asset][tf] = FastHorizonEngine(frame, k=k, mitigation_mode=mitigation)
            
            if len(frame) >= 28:
                adx_df = frame.ta.adx(length=14)
                if adx_df is not None and not adx_df.empty:
                    self.cached_adx[asset][tf] = adx_df.iloc[:, 0].fillna(0).values
                else:
                    self.cached_adx[asset][tf] = np.zeros(len(frame))
            else:
                self.cached_adx[asset][tf] = np.zeros(len(frame))
                
            if len(frame) >= 15:
                atr_s = frame.ta.atr(length=14)
                if atr_s is not None and not atr_s.empty:
                    self.cached_atr[asset][tf] = atr_s.fillna(frame['close'] * 0.005).values
                else:
                    self.cached_atr[asset][tf] = (frame['close'] * 0.005).values
            else:
                self.cached_atr[asset][tf] = (frame['close'] * 0.005).values
                
        self.cached_downsamples[asset] = ds
        return ds

    def _monte_carlo(self, pnl_list: List[float], initial_capital: float) -> float:
        if len(pnl_list) < 5:
            return 0.0
        pnl_arr = np.array(pnl_list)
        drawdowns = []
        for _ in range(500):
            shuffled = np.random.permutation(pnl_arr)
            eq = initial_capital + np.cumsum(shuffled)
            eq = np.insert(eq, 0, initial_capital)
            running_max = np.maximum.accumulate(eq)
            dd = (running_max - eq) / running_max
            drawdowns.append(np.max(dd) * 100.0)
        return float(np.percentile(drawdowns, 95))

    def run_single_simulation(self, asset: str, set_name: str, config: dict, ds: Dict[str, pd.DataFrame]) -> OptimizedInstitutionalPerf:
        htf_tf = config['htf']
        mtf_tf = config['mtf']
        ltf_tf = config['ltf']
        
        df_htf = ds[htf_tf]
        df_mtf = ds[mtf_tf]
        df_ltf = ds[ltf_tf]
        
        htf_engine = self.cached_engines[asset][htf_tf]
        mtf_engine = self.cached_engines[asset][mtf_tf]
        ltf_engine = self.cached_engines[asset][ltf_tf]
        
        htf_adx_arr = self.cached_adx[asset][htf_tf]
        ltf_atr_arr = self.cached_atr[asset][ltf_tf]
        
        if len(df_ltf) < 50:
            return None
            
        htf_ts = df_htf['datetime'].values
        mtf_ts = df_mtf['datetime'].values
        ltf_ts = df_ltf['datetime'].values
        
        htf_idx_map = np.searchsorted(htf_ts, ltf_ts, side='right') - 1
        mtf_idx_map = np.searchsorted(mtf_ts, ltf_ts, side='right') - 1
        
        risk_guardian = RiskGuardian()
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0
        daily_equity = {}
        
        trades = []
        trade_pnls = []
        in_trade = False
        state = StrategyState.IDLE
        active_intent: Optional[OrderIntent] = None
        
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        partial_tp_price = 0.0
        position_size = 0.0
        has_taken_partial = False
        
        total_fee_drag = 0.0
        total_slippage_drag = 0.0
        
        warmup = max(30, min(100, len(df_ltf) // 10))
        closes = df_ltf['close'].values
        highs = df_ltf['high'].values
        lows = df_ltf['low'].values
        datetimes = df_ltf['datetime'].values
        
        # Minimum Stop Loss Distance to prevent fee drag destruction (at least 0.8% price distance)
        MIN_SL_PCT = 0.008
        
        for i in range(warmup, len(df_ltf)):
            current_time = datetimes[i]
            current_date = str(current_time)[:10]
            current_close = closes[i]
            current_high = highs[i]
            current_low = lows[i]
            current_atr = ltf_atr_arr[i] if i < len(ltf_atr_arr) else current_close * 0.005
            
            slip_pct = self.base_slippage + (0.02 * (current_atr / current_close))
            
            h_idx = max(0, htf_idx_map[i])
            m_idx = max(0, mtf_idx_map[i])
            
            htf_trend = htf_engine.trends[h_idx]
            mtf_trend = mtf_engine.trends[m_idx]
            ltf_trend = ltf_engine.trends[i]
            
            htf_high = htf_engine.last_highs[h_idx]
            htf_low = htf_engine.last_lows[h_idx]
            mtf_zones = mtf_engine.active_zones[m_idx]
            ltf_high = ltf_engine.last_highs[i]
            ltf_low = ltf_engine.last_lows[i]
            htf_adx = htf_adx_arr[h_idx] if h_idx < len(htf_adx_arr) else 0.0
            
            # Position management
            if in_trade:
                side = active_intent.side.name
                
                # Partial TP check (+2R)
                if not has_taken_partial:
                    if side == 'LONG' and current_high >= partial_tp_price:
                        realized_exit = partial_tp_price * (1.0 - slip_pct)
                        fee_exit = realized_exit * (position_size * 0.5) * self.taker_exit_fee
                        net_p = ((realized_exit - entry_price) * (position_size * 0.5)) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (partial_tp_price - realized_exit) * (position_size * 0.5)
                        
                        position_size *= 0.5
                        # Fee-buffered Break Even (Move SL above entry by total roundtrip friction)
                        sl_price = entry_price * (1.0 + (self.maker_entry_fee + self.taker_exit_fee + slip_pct))
                        has_taken_partial = True
                        trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': net_p, 'capital': capital})
                        
                    elif side == 'SHORT' and current_low <= partial_tp_price:
                        realized_exit = partial_tp_price * (1.0 + slip_pct)
                        fee_exit = realized_exit * (position_size * 0.5) * self.taker_exit_fee
                        net_p = ((entry_price - realized_exit) * (position_size * 0.5)) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (realized_exit - partial_tp_price) * (position_size * 0.5)
                        
                        position_size *= 0.5
                        sl_price = entry_price * (1.0 - (self.maker_entry_fee + self.taker_exit_fee + slip_pct))
                        has_taken_partial = True
                        trades.append({'time': current_time, 'type': 'EXIT_PARTIAL_TP', 'pnl': net_p, 'capital': capital})
                
                # SL / BE and Full TP Check
                if side == 'LONG':
                    if current_low <= sl_price:
                        realized_exit = sl_price * (1.0 - slip_pct)
                        fee_exit = realized_exit * position_size * self.taker_exit_fee
                        net_p = ((realized_exit - entry_price) * position_size) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (sl_price - realized_exit) * position_size
                        
                        in_trade = False
                        has_taken_partial = False
                        state = StrategyState.IDLE
                        active_intent = None
                        trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': net_p, 'capital': capital})
                    elif current_high >= tp_price:
                        realized_exit = tp_price * (1.0 - slip_pct)
                        fee_exit = realized_exit * position_size * self.taker_exit_fee
                        net_p = ((realized_exit - entry_price) * position_size) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (tp_price - realized_exit) * position_size
                        
                        in_trade = False
                        has_taken_partial = False
                        state = StrategyState.IDLE
                        active_intent = None
                        trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': net_p, 'capital': capital})
                else: # SHORT
                    if current_high >= sl_price:
                        realized_exit = sl_price * (1.0 + slip_pct)
                        fee_exit = realized_exit * position_size * self.taker_exit_fee
                        net_p = ((entry_price - realized_exit) * position_size) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (realized_exit - sl_price) * position_size
                        
                        in_trade = False
                        has_taken_partial = False
                        state = StrategyState.IDLE
                        active_intent = None
                        trades.append({'time': current_time, 'type': 'EXIT_SL_OR_BE', 'pnl': net_p, 'capital': capital})
                    elif current_low <= tp_price:
                        realized_exit = tp_price * (1.0 + slip_pct)
                        fee_exit = realized_exit * position_size * self.taker_exit_fee
                        net_p = ((entry_price - realized_exit) * position_size) - fee_exit
                        
                        capital += net_p
                        trade_pnls.append(net_p)
                        total_fee_drag += fee_exit
                        total_slippage_drag += (realized_exit - tp_price) * position_size
                        
                        in_trade = False
                        has_taken_partial = False
                        state = StrategyState.IDLE
                        active_intent = None
                        trades.append({'time': current_time, 'type': 'EXIT_TP', 'pnl': net_p, 'capital': capital})
                
                # Drawdown Tracking
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100
                if dd > max_drawdown:
                    max_drawdown = dd
                    
                daily_equity[current_date] = capital
                continue

            # -------------------------------------------------------------
            # Strategy State Machine with Friction Immunity Filter
            # -------------------------------------------------------------
            if state == StrategyState.IDLE:
                if htf_trend in [Trend.BULLISH, Trend.BEARISH]:
                    if htf_adx >= 25.0:
                        state = StrategyState.HTF_BIAS_CONFIRMED
                        
            elif state == StrategyState.HTF_BIAS_CONFIRMED:
                if htf_trend == Trend.BULLISH and mtf_trend == Trend.BEARISH:
                    state = StrategyState.AWAITING_MTF_ALIGNMENT
                elif htf_trend == Trend.BEARISH and mtf_trend == Trend.BULLISH:
                    state = StrategyState.AWAITING_MTF_ALIGNMENT
                    
            elif state == StrategyState.AWAITING_MTF_ALIGNMENT:
                if htf_trend == mtf_trend and htf_trend != Trend.NEUTRAL:
                    state = StrategyState.MTF_ALIGNED
                    
            elif state == StrategyState.MTF_ALIGNED:
                if len(mtf_zones) > 0:
                    state = StrategyState.WAITING_MTF_KEYZONE
                    
            elif state == StrategyState.WAITING_MTF_KEYZONE:
                tapped = False
                for zone in mtf_zones:
                    if htf_trend == Trend.BULLISH and zone.zone_type in [KeyzoneType.FVG_BULLISH, KeyzoneType.OB_BULLISH]:
                        if current_low <= zone.top and current_high >= zone.bottom:
                            tapped = True
                    elif htf_trend == Trend.BEARISH and zone.zone_type in [KeyzoneType.FVG_BEARISH, KeyzoneType.OB_BEARISH]:
                        if current_high >= zone.bottom and current_low <= zone.top:
                            tapped = True
                if tapped:
                    state = StrategyState.AWAITING_LTF_ENTRY
                    
            elif state == StrategyState.AWAITING_LTF_ENTRY:
                if ltf_trend == htf_trend:
                    is_valid_zone = False
                    if htf_high and htf_low:
                        fib_50 = htf_low.price + ((htf_high.price - htf_low.price) * 0.5)
                        if htf_trend == Trend.BULLISH and current_close <= fib_50:
                            is_valid_zone = True
                        elif htf_trend == Trend.BEARISH and current_close >= fib_50:
                            is_valid_zone = True
                            
                    if is_valid_zone:
                        side = OrderSide.LONG if htf_trend == Trend.BULLISH else OrderSide.SHORT
                        sl = ltf_low.price if (side == OrderSide.LONG and ltf_low) else (ltf_high.price if ltf_high else 0.0)
                        tp = htf_high.price if (side == OrderSide.LONG and htf_high) else (htf_low.price if htf_low else 0.0)
                        
                        # Apply Minimum SL Distance Filter to block micro-chop fee traps
                        sl_dist_pct = abs(current_close - sl) / current_close if sl > 0 else 0.0
                        
                        if sl != 0.0 and tp != 0.0 and sl_dist_pct >= MIN_SL_PCT:
                            intent = OrderIntent(
                                asset=asset,
                                timeframe_set=set_name,
                                side=side,
                                entry_price=current_close,
                                sl_price=sl,
                                tp_price=tp,
                                risk_percentage=0.01
                            )
                            
                            if risk_guardian.evaluate_intent(intent, current_equity=capital):
                                active_intent = intent
                                in_trade = True
                                entry_price = current_close
                                sl_price = intent.sl_price
                                tp_price = intent.tp_price
                                has_taken_partial = False
                                
                                risk_dist = abs(entry_price - sl_price)
                                position_size = (capital * intent.risk_percentage) / risk_dist
                                
                                # Deduct maker limit entry commission
                                fee_entry = entry_price * position_size * self.maker_entry_fee
                                capital -= fee_entry
                                total_fee_drag += fee_entry
                                
                                if intent.side.name == 'LONG':
                                    partial_tp_price = entry_price + (risk_dist * 2.0)
                                else:
                                    partial_tp_price = entry_price - (risk_dist * 2.0)
                                    
                                trades.append({'time': current_time, 'type': 'ENTRY', 'side': intent.side.name, 'price': entry_price, 'sl': sl_price, 'tp': tp_price})
                                state = StrategyState.POSITION_ACTIVE
                                
            if htf_trend == Trend.NEUTRAL and not in_trade:
                state = StrategyState.IDLE
                
            daily_equity[current_date] = capital

        exits = [t for t in trades if t['type'].startswith('EXIT_SL') or t['type'].startswith('EXIT_TP')]
        partials = [t for t in trades if t['type'] == 'EXIT_PARTIAL_TP']
        wins = [t for t in exits if t['pnl'] > 0]
        losses = [t for t in exits if t['pnl'] < 0]
        be_trades = [t for t in exits if t['pnl'] == 0]
        
        gross_profit = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        net_profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        
        non_losses = len(wins) + len(be_trades)
        win_rate = (non_losses / len(exits)) * 100 if len(exits) > 0 else 0.0
        
        total_net_pnl = capital - self.initial_capital
        net_ret_pct = (total_net_pnl / self.initial_capital) * 100
        
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
            
        calmar = (cagr / max_drawdown) if max_drawdown > 0 else 0.0
        mc_95_dd = self._monte_carlo(trade_pnls, self.initial_capital)
        
        start_str = str(df_ltf.iloc[0]['datetime'])[:10]
        end_str = str(df_ltf.iloc[-1]['datetime'])[:10]
        
        return OptimizedInstitutionalPerf(
            asset=asset,
            set_name=set_name,
            htf_tf=htf_tf,
            mtf_tf=mtf_tf,
            ltf_tf=ltf_tf,
            start_date=start_str,
            end_date=end_str,
            initial_capital=self.initial_capital,
            final_capital=capital,
            net_profit=total_net_pnl,
            total_fee_drag=total_fee_drag,
            total_slippage_drag=total_slippage_drag,
            net_return_pct=net_ret_pct,
            cagr_pct=cagr,
            max_drawdown_pct=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=len(exits),
            wins_4r=len(wins),
            losses_1r=len(losses),
            break_evens=len(be_trades),
            partials_2r=len(partials),
            win_rate_non_loss=win_rate,
            profit_factor=net_profit_factor,
            mc_95_max_dd=mc_95_dd
        )

    def run_master_matrix(self):
        print("=" * 115)
        print("🏛️  APEX QUANT OS: OPTIMIZED INSTITUTIONAL MULTI-ASSET MATRIX")
        print("   Friction Protected: Maker Limit Entries + 0.8% Min SL Filter + Fee-Buffered Break-Even")
        print("=" * 115)
        
        master_t0 = time.time()
        results: List[OptimizedInstitutionalPerf] = []
        
        for asset in self.assets.keys():
            ds = self.load_and_downsample_asset(asset)
            print(f"\n[⚡ RUNNING SUITE] Asset: {asset}")
            print("─" * 115)
            for set_name, config in self.timeframe_sets.items():
                print(f"  ▶ [{set_name:<25}] (HTF:{config['htf']:<3} -> MTF:{config['mtf']:<3} -> LTF:{config['ltf']:<5})...", end="", flush=True)
                t_sub = time.time()
                perf = self.run_single_simulation(asset, set_name, config, ds)
                if perf:
                    results.append(perf)
                    print(f" Done ({time.time()-t_sub:4.2f}s) | Trades: {perf.total_trades:3d} | WR: {perf.win_rate_non_loss:4.1f}% | Net ROI: {perf.net_return_pct:+6.1f}% | Sharpe: {perf.sharpe_ratio:4.2f} | MaxDD: {perf.max_drawdown_pct:4.1f}%")
                    
        # Summary Matrix Display
        print("\n" + "=" * 122)
        print("                               📊 OPTIMIZED INSTITUTIONAL RISK & ALPHA MATRIX")
        print("=" * 122)
        print(f"{'Asset':<8} | {'Strategy Set':<25} | {'Trades':<6} | {'WR (Net)':<8} | {'Net Profit':<11} | {'Fee Drag':<10} | {'Sharpe':<7} | {'Sortino':<7} | {'Max DD%':<8} | {'MC 95% DD':<9}")
        print("─" * 122)
        
        total_initial_fund = 0.0
        total_final_fund = 0.0
        total_trades_all = 0
        total_wins_all = 0
        total_losses_all = 0
        total_be_all = 0
        total_fee_all = 0.0
        total_slip_all = 0.0
        
        for r in results:
            total_initial_fund += r.initial_capital
            total_final_fund += r.final_capital
            total_trades_all += r.total_trades
            total_wins_all += r.wins_4r
            total_losses_all += r.losses_1r
            total_be_all += r.break_evens
            total_fee_all += r.total_fee_drag
            total_slip_all += r.total_slippage_drag
            
            print(f"{r.asset:<8} | {r.set_name:<25} | {r.total_trades:<6d} | {r.win_rate_non_loss:>6.1f}%  | ${r.net_profit:>+9.2f} | ${r.total_fee_drag:>8.2f} | {r.sharpe_ratio:>6.2f} | {r.sortino_ratio:>6.2f} | {r.max_drawdown_pct:>6.2f}% | {r.mc_95_max_dd:>7.2f}%")
            
        print("─" * 122)
        total_fund_roi = ((total_final_fund - total_initial_fund) / total_initial_fund) * 100 if total_initial_fund > 0 else 0.0
        fund_wr = ((total_wins_all + total_be_all) / total_trades_all) * 100 if total_trades_all > 0 else 0.0
        
        print("\n" + "=" * 90)
        print("🏆 CONSOLIDATED OPTIMIZED PORTFOLIO TEAR SHEET")
        print("=" * 90)
        print(f"Total Multi-Strategy Initial Capital: ${total_initial_fund:,.2f}")
        print(f"Total Multi-Strategy Final Capital:   ${total_final_fund:,.2f}")
        print(f"Total Net Withdrawable PnL:          ${(total_final_fund - total_initial_fund):+,.2f} ({total_fund_roi:+.2f}%)")
        print(f"Total Exchange Commission Paid:       ${total_fee_all:,.2f}")
        print(f"Total Volatility Slippage Absorbed:   ${total_slip_all:,.2f}")
        print(f"Total System Trades Executed:         {total_trades_all}")
        print(f"Total System 4R Target Hits:          {total_wins_all}")
        print(f"Total System 2R Partial Break-Evens:  {total_be_all}")
        print(f"Total System Stop-Losses:             {total_losses_all}")
        print(f"Consolidated Non-Loss Win Rate:       {fund_wr:.2f}%")
        print(f"Total Computation Time:               {time.time() - master_t0:.2f} seconds")
        print("=" * 90)

if __name__ == "__main__":
    matrix = OptimizedInstitutionalMatrix(initial_capital_per_cartridge=10000.0)
    matrix.run_master_matrix()
