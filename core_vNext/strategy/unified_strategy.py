import pandas as pd
from core_vNext.structure.swing_engine import SwingEngine, Trend, SwingType
from core_vNext.structure.keyzone_engine import KeyzoneEngine, KeyzoneType
from core_vNext.strategy.strategy_state_machine import StateMachine, StrategyState
from core_vNext.execution.order_intent import OrderIntent, OrderSide
from core_vNext.risk.risk_guardian import RiskGuardian
import pandas_ta as ta

class UnifiedStrategy:
    """
    The core Master Strategy connecting the HTF, MTF, and LTF structural engines.
    Operates strictly deterministically based on structural states.
    """
    def __init__(self, asset: str, timeframe_set: str, htf_k: int = 3, mtf_k: int = 3, ltf_k: int = 2):
        self.asset = asset
        self.timeframe_set = timeframe_set
        
        self.fsm = StateMachine(asset, timeframe_set)
        self.risk_guardian = RiskGuardian()
        
        # Instantiate layer engines according to specification parameters
        self.htf_swings = SwingEngine(k=htf_k)
        self.htf_zones = KeyzoneEngine(mitigation_mode='full_overlap')
        
        self.mtf_swings = SwingEngine(k=mtf_k)
        self.mtf_zones = KeyzoneEngine(mitigation_mode='touch')
        
        self.ltf_swings = SwingEngine(k=ltf_k)
        self.ltf_zones = KeyzoneEngine(mitigation_mode='touch')

    def process_multi_horizon(self, htf_df: pd.DataFrame, mtf_df: pd.DataFrame, ltf_df: pd.DataFrame):
        """
        Ingests the multi-horizon data and ticks the state machine.
        """
        # 1. Update engines
        self.htf_swings.process_batch(htf_df)
        self.htf_zones.process_batch(htf_df)
        
        self.mtf_swings.process_batch(mtf_df)
        self.mtf_zones.process_batch(mtf_df)
        
        self.ltf_swings.process_batch(ltf_df)
        self.ltf_zones.process_batch(ltf_df)
        
        # Calculate HTF ADX (requires at least 28 bars for 14-period ADX to start smoothing)
        htf_adx = 0.0
        if len(htf_df) > 28:
            adx_series = htf_df.ta.adx(length=14)
            if adx_series is not None and not adx_series.empty:
                htf_adx = adx_series.iloc[-1].iloc[0] # First column is ADX_14
        
        # 2. Tick State Machine
        self._tick_state_machine(ltf_df.iloc[-1]['close'] if not ltf_df.empty else 0.0, htf_adx, ltf_df)
        
    def _tick_state_machine(self, current_price: float, htf_adx: float, ltf_df: pd.DataFrame):
        current_state = self.fsm.state
        htf_trend = self.htf_swings.current_trend
        mtf_trend = self.mtf_swings.current_trend
        ltf_trend = self.ltf_swings.current_trend
        
        if current_state == StrategyState.IDLE:
            if htf_trend in [Trend.BULLISH, Trend.BEARISH]:
                if htf_adx >= 25.0:
                    self.fsm.transition_to(StrategyState.HTF_BIAS_CONFIRMED)
                
        elif current_state == StrategyState.HTF_BIAS_CONFIRMED:
            # Look for MTF Countertrend Pullback
            if htf_trend == Trend.BULLISH and mtf_trend == Trend.BEARISH:
                self.fsm.transition_to(StrategyState.AWAITING_MTF_ALIGNMENT)
            elif htf_trend == Trend.BEARISH and mtf_trend == Trend.BULLISH:
                self.fsm.transition_to(StrategyState.AWAITING_MTF_ALIGNMENT)
                
        elif current_state == StrategyState.AWAITING_MTF_ALIGNMENT:
            # Look for MTF Realignment with HTF
            if htf_trend == mtf_trend and htf_trend != Trend.NEUTRAL:
                self.fsm.transition_to(StrategyState.MTF_ALIGNED)
                
        elif current_state == StrategyState.MTF_ALIGNED:
            active_mtf_zones = self.mtf_zones.get_active_zones()
            if len(active_mtf_zones) > 0:
                self.fsm.transition_to(StrategyState.WAITING_MTF_KEYZONE)
                
        elif current_state == StrategyState.WAITING_MTF_KEYZONE:
            # Check if price tapped the MTF Keyzone
            active_mtf_zones = self.mtf_zones.get_active_zones()
            tapped = False
            for zone in active_mtf_zones:
                if htf_trend == Trend.BULLISH and zone.zone_type in [KeyzoneType.FVG_BULLISH, KeyzoneType.OB_BULLISH]:
                    if current_price <= zone.top and current_price >= zone.bottom:
                        tapped = True
                elif htf_trend == Trend.BEARISH and zone.zone_type in [KeyzoneType.FVG_BEARISH, KeyzoneType.OB_BEARISH]:
                    if current_price >= zone.bottom and current_price <= zone.top:
                        tapped = True
            
            if tapped:
                self.fsm.transition_to(StrategyState.MTF_KEYZONE_TOUCHED)
                self.fsm.transition_to(StrategyState.AWAITING_LTF_ENTRY)
                
        elif current_state == StrategyState.AWAITING_LTF_ENTRY:
            # LTF Structural shift aligns with HTF/MTF
            if ltf_trend == htf_trend:
                
                # We have a candidate entry. 
                # Premium/Discount Matrix Filter
                is_valid_zone = False
                if self.htf_swings.last_confirmed_high and self.htf_swings.last_confirmed_low:
                    htf_high = self.htf_swings.last_confirmed_high.price
                    htf_low = self.htf_swings.last_confirmed_low.price
                    fib_50 = htf_low + ((htf_high - htf_low) * 0.5)
                    
                    if htf_trend == Trend.BULLISH and current_price <= fib_50: # Discount Zone
                        is_valid_zone = True
                    elif htf_trend == Trend.BEARISH and current_price >= fib_50: # Premium Zone
                        is_valid_zone = True
                
                if is_valid_zone:
                    # Create OrderIntent and pass to RiskGuardian
                    side = OrderSide.LONG if htf_trend == Trend.BULLISH else OrderSide.SHORT
                    
                    # Structural SL is the last confirmed LTF low/high
                    sl = 0.0
                    if side == OrderSide.LONG and self.ltf_swings.last_confirmed_low:
                        sl = self.ltf_swings.last_confirmed_low.price
                    elif side == OrderSide.SHORT and self.ltf_swings.last_confirmed_high:
                        sl = self.ltf_swings.last_confirmed_high.price
                        
                    # HTF Target is the last confirmed HTF high/low (weak swing assumption)
                    tp = 0.0
                    if side == OrderSide.LONG and self.htf_swings.last_confirmed_high:
                        tp = self.htf_swings.last_confirmed_high.price
                    elif side == OrderSide.SHORT and self.htf_swings.last_confirmed_low:
                        tp = self.htf_swings.last_confirmed_low.price
                        
                    if sl != 0.0 and tp != 0.0:
                        intent = OrderIntent(
                            asset=self.asset,
                            timeframe_set=self.timeframe_set,
                            side=side,
                            entry_price=current_price,
                            sl_price=sl,
                            tp_price=tp,
                            risk_percentage=0.01 # 1% max per spec
                        )
                        
                        if self.risk_guardian.evaluate_intent(intent, current_equity=100000.0): # Mock equity
                            self.fsm.active_intent = intent
                            self.fsm.transition_to(StrategyState.RISK_APPROVED)
                            self.fsm.transition_to(StrategyState.ORDER_SUBMITTED)
                        
        # If HTF structure invalidates at any point, kill the setup
        if htf_trend == Trend.NEUTRAL:
            self.fsm.reset()
