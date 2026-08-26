# filename: filters/risk_filters_engine_v1.py
import logging
from datetime import datetime, timezone
from typing import List, Optional
from config.global_config import GLOBAL_CONFIG
from core.interfaces.contracts import TradePlan, DecisionSnapshot, StrategyDecision, SignalDirection

class ApexRiskFiltersEngineV1:
    """
    Module 4: Risk & Filters Engine (Version 1.1.0).
    Enforces the strict 1% cash risk limit and surfaces the precise
    allocated lot sizes into the global tracking contract structure.
    """
    def __init__(self, current_account_balance: float = 1000.0):
        self.account_balance = current_account_balance
        self.logger = logging.getLogger("ApexRiskFiltersEngineV1")

    def evaluate_execution_safety(
        self, 
        plan: TradePlan, 
        active_portfolio_symbols: List[str], 
        is_macro_news_active: bool = False
    ) -> DecisionSnapshot:
        """
        Evaluates safety thresholds and embeds calculated allocation targets
        directly into the returned DecisionSnapshot token.
        """
        symbol = plan.symbol
        
        dummy_decision = StrategyDecision(
            symbol=symbol,
            direction=plan.direction,
            timeframe_a_bias=MarketTrend.NEUTRAL if plan.direction == SignalDirection.WAIT else MarketTrend.BULLISH,
            timeframe_b_aligned=True,
            timeframe_c_triggered=True,
            convergence_score=100.0,
            structural_anchor_levels={},
            timestamp=datetime.now(timezone.utc)
        )

        # Gate 0: Short-circuit if upstream layers passed an invalid layout
        if not plan.is_valid or plan.direction == SignalDirection.WAIT:
            return self._generate_blocked_snapshot(
                symbol, dummy_decision, plan, "UPSTREAM_PLAN_INVALID"
            )

        # Gate 1: News Safety Filter
        if is_macro_news_active:
            return self._generate_blocked_snapshot(
                symbol, dummy_decision, plan, "BLOCK_MACRO_ECONOMIC_NEWS_ACTIVE", news_gate=False
            )

        # Gate 2: Systematic Co-exposure Filter (Abstract Group Cap)
        if len(active_portfolio_symbols) >= 3:
            return self._generate_blocked_snapshot(
                symbol, dummy_decision, plan, "BLOCK_MAX_SYSTEMIC_CORRELATION_BREACHED", portfolio_gate=False
            )

        # Gate 3: Sizing Math Calculation Execution
        risk_distance = abs(plan.entry_price - plan.stop_loss)
        if risk_distance == 0.0:
            return self._generate_blocked_snapshot(
                symbol, dummy_decision, plan, "BLOCK_INVALID_RISK_DISTANCE_ZERO"
            )

        # Cash at Risk calculation matching strict 1% allocation thresholds
        cash_at_risk = self.account_balance * (GLOBAL_CONFIG.PORTFOLIO_RISK_PER_TRADE_PCT / 100.0)
        allocated_lot_size = cash_at_risk / risk_distance

        return DecisionSnapshot(
            symbol=symbol,
            strategy_decision=dummy_decision,
            trade_plan=plan,
            news_gate_pass=True,
            spread_gate_pass=True,
            session_gate_pass=True,
            volatility_gate_pass=True,
            portfolio_gate_pass=True,
            allocated_lot_size=float(allocated_lot_size),
            cash_at_risk=float(cash_at_risk),
            proceed=True,
            rejection_reason=None,
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_blocked_snapshot(
        self, 
        symbol: str, 
        decision: StrategyDecision, 
        plan: TradePlan,
        reason: str,
        news_gate: bool = True,
        portfolio_gate: bool = True
    ) -> DecisionSnapshot:
        return DecisionSnapshot(
            symbol=symbol,
            strategy_decision=decision,
            trade_plan=plan,
            news_gate_pass=news_gate,
            spread_gate_pass=True,
            session_gate_pass=True,
            volatility_gate_pass=True,
            portfolio_gate_pass=portfolio_gate,
            allocated_lot_size=0.0,
            cash_at_risk=0.0,
            proceed=False,
            rejection_reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
from core.interfaces.contracts import MarketTrend # Internal type import safety hook
