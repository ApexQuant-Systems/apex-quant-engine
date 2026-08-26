# filename: data_pipeline/pipeline_coordinator_tests.py
import unittest
import asyncio
from data_pipeline.binance_adapter import BinanceExchangeAdapter
from data_pipeline.data_validator import ApexDataValidator
from data_pipeline.historical_loader import ApexHistoricalLoader
from data_pipeline.live_feed import ApexLiveFeedEngine
from data_pipeline.pipeline_coordinator import ApexPipelineCoordinator

class TestPipelineCoordinator(unittest.TestCase):
    def setUp(self):
        self.adapter = BinanceExchangeAdapter()
        self.validator = ApexDataValidator()
        self.loader = ApexHistoricalLoader(self.adapter, self.validator)
        self.coordinator = ApexPipelineCoordinator(self.adapter, self.loader)

    def test_module_1_8_historical_sync_sequence(self):
        # Test historical seed execution across standard Horizon Set 4 parameters
        success = self.coordinator.initialize_historical_sync(horizon_set=4, backfill_limit=5)
        self.assertTrue(success)
        self.assertIn("BTCUSDT", self.coordinator.synchronized_symbols)

    def test_live_handover_transition(self):
        live_feed = ApexLiveFeedEngine(target_symbols=["BTCUSDT", "ETHUSDT"])
        self.coordinator.synchronized_symbols = ["BTCUSDT", "ETHUSDT"]
        
        # Test non-blocking asynchronous live streaming delivery via the coordinator container
        asyncio.run(self.coordinator.launch_live_stream_pipeline(live_feed, stream_cycles=2))
        self.assertFalse(live_feed.is_running)

if __name__ == "__main__":
    unittest.main()
