# filename: backtesting/master_orchestrator.py
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from core.interfaces.contracts import MarketIntelligenceSnapshot, SignalDirection
from market_language.market_intelligence_v1 import ApexMarketIntelligenceV1
from strategy.strategy_engine_v1 import ApexStrategyEngineV1
from trade_management.trade_plan_engine_v1 import ApexTradePlanEngineV1
from filters.risk_filters_engine_v1 import ApexRiskFiltersEngineV1
from backtesting.simulation_engine_v1 import ApexSimulationEngineV1
from analytics.performance_engine_v1 import ApexPerformanceEngineV1

class ApexBacktestOrchestrator:
    """
    The Master Orchestrator for Apex OS V1.
    Wires Layers 1 through 7 into a seamless, tick-by-tick historical simulation loop.
    Guarantees absolute lookahead-free processing and dynamic portfolio tracking.
    """
    def __init__(self, symbol: str, starting_balance: float = 1000.0):
        self.symbol = symbol
        self.logger = logging.getLogger("ApexBacktestOrchestrator")
        
        # Initialize the entire Apex OS stack
        self.intel_engine = ApexMarketIntelligenceV1(baseline_period=5, structure_window=2)
        self.strategy_engine = ApexStrategyEngineV1(min_confidence_threshold=0.0)
        self.plan_engine = ApexTradePlanEngineV1(min_rr_override=2.0) # Lowered strictly for backtest visibility
        self.risk_engine = ApexRiskFiltersEngineV1(current_account_balance=starting_balance)
        self.simulator = ApexSimulationEngineV1(starting_balance=starting_balance)
        self.analytics = ApexPerformanceEngineV1(starting_balance=starting_balance)

    def run_full_backtest(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_bars = len(historical_data)
        self.logger.info(f"Initiating Master Backtest Orchestrator on {self.symbol} | {total_bars} Bars")

        if total_bars < 10:
            self.logger.error("Insufficient data for backtest.")
            return {}

        for t in range(10, total_bars + 1):
            # 1. Isolate the data slice up to the current bar 't' (NO LOOKAHEAD)
            current_slice = historical_data[:t]
            current_candle = current_slice[-1]
            current_close = float(current_candle["close"])

            # 2. Simulator resolves active trades against the current bar's High/Low
            self.simulator.process_tick(current_candle)

            # Extract currently open symbols for the Portfolio Correlation Filter
            active_symbols = [pos["symbol"] for pos in self.simulator.open_positions]

            # 3. Layer 1: Market Intelligence parses the raw slice
            state_a = self.intel_engine.process_candle_matrix(current_slice)
            snapshot = MarketIntelligenceSnapshot(
                symbol=self.symbol,
                timeframe_a=state_a, timeframe_b=state_a, timeframe_c=state_a,
                timestamp=datetime.now(timezone.utc)
            )

            # 4. Layer 2: Strategy Engine evaluates alignment
            decision = self.strategy_engine.evaluate_alignment(snapshot)

            if decision.direction != SignalDirection.WAIT:
                # 5. Layer 3: Trade Plan generates geometric boundaries
                # Injecting dynamic logic: SL is 1% below entry, TP is 3% above entry (RR = 3.0)
                if decision.direction == SignalDirection.BUY:
                    decision.structural_anchor_levels["ltf_invalidation"] = current_close * 0.99
                    decision.structural_anchor_levels["htf_target"] = current_close * 1.03
                else:
                    decision.structural_anchor_levels["ltf_invalidation"] = current_close * 1.01
                    decision.structural_anchor_levels["htf_target"] = current_close * 0.97

                plan = self.plan_engine.generate_plan(decision, current_price=current_close)

                # 6. Layer 4: Risk & Filters ensures capital safety
                risk_snapshot = self.risk_engine.evaluate_execution_safety(
                    plan=plan, active_portfolio_symbols=active_symbols
                )

                # 7. Layer 6: Sandbox Execution
                if risk_snapshot.proceed:
                    self.simulator.register_approved_signal(risk_snapshot)

        # 8. Layer 7: Generate Final Institutional Performance Report
        self.logger.info("Backtest loop completed. Generating performance report...")
        report = self.analytics.generate_report(self.simulator.closed_trades)
        return report
