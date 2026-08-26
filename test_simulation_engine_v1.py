# filename: test_simulation_engine_v1.py
import unittest
from datetime import datetime, timezone
from core.interfaces.contracts import DecisionSnapshot, TradePlan, StrategyDecision, SignalDirection, MarketTrend
from backtesting.simulation_engine_v1 import ApexSimulationEngineV1

class TestSimulationEngineV1(unittest.TestCase):
    def setUp(self):
        self.simulator = ApexSimulationEngineV1(starting_balance=1000.0)
        
        dummy_decision = StrategyDecision(
            symbol="BTCUSDT", direction=SignalDirection.BUY, timeframe_a_bias=MarketTrend.BULLISH,
            timeframe_b_aligned=True, timeframe_c_triggered=True, convergence_score=100.0,
            structural_anchor_levels={}, timestamp=datetime.now(timezone.utc)
        )
        
        # Valid Buy Layout: Entry 60000, SL 59000 (Risk=1000), TP 64000 (Reward=4000) -> 1:4 RR
        valid_plan = TradePlan(
            symbol="BTCUSDT", direction=SignalDirection.BUY, entry_price=60000.0, stop_loss=59000.0, 
            take_profit=64000.0, risk_reward_ratio=4.0, is_valid=True, timestamp=datetime.now(timezone.utc)
        )
        
        # 1% risk on $1000 balance = $10. Volume = 10 / 1000 = 0.01
        self.snapshot = DecisionSnapshot(
            symbol="BTCUSDT", strategy_decision=dummy_decision, trade_plan=valid_plan,
            news_gate_pass=True, spread_gate_pass=True, session_gate_pass=True,
            volatility_gate_pass=True, portfolio_gate_pass=True,
            allocated_lot_size=0.01, cash_at_risk=10.0, proceed=True,
            timestamp=datetime.now(timezone.utc)
        )

    def test_trade_resolution_win_logic(self):
        self.simulator.register_approved_signal(self.snapshot)
        self.assertEqual(len(self.simulator.open_positions), 1)

        # Feed a bar that hits the Take Profit (High >= 64000)
        bullish_candle = {"high": 64500.0, "low": 60000.0, "timestamp": "2026-06-20T10:00:00Z"}
        self.simulator.process_tick(bullish_candle)
        
        self.assertEqual(len(self.simulator.open_positions), 0)
        self.assertEqual(len(self.simulator.closed_trades), 1)
        
        # Verify 1:4 RR PnL ($10 risk * 4 = $40 profit)
        self.assertEqual(self.simulator.closed_trades[0]["outcome"], "WIN")
        self.assertAlmostEqual(self.simulator.closed_trades[0]["pnl"], 40.0)
        self.assertAlmostEqual(self.simulator.current_balance, 1040.0)

    def test_pessimistic_stop_loss_priority(self):
        self.simulator.register_approved_signal(self.snapshot)
        
        # Feed a violently volatile bar that hits both TP and SL.
        # The simulator MUST assume the SL hit first to prevent fake backtest success.
        volatile_candle = {"high": 65000.0, "low": 58000.0, "timestamp": "2026-06-20T10:00:00Z"}
        self.simulator.process_tick(volatile_candle)
        
        self.assertEqual(self.simulator.closed_trades[0]["outcome"], "LOSS")
        self.assertAlmostEqual(self.simulator.closed_trades[0]["pnl"], -10.0)
        self.assertAlmostEqual(self.simulator.current_balance, 990.0)

if __name__ == "__main__":
    unittest.main()
