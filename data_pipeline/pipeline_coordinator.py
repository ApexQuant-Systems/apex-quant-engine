# filename: data_pipeline/pipeline_coordinator.py
import asyncio
import logging
from typing import List, Dict, Any
from data_pipeline.asset_manager import ApexAssetManager
from data_pipeline.timeframe_manager import ApexTimeframeManager
from data_pipeline.exchange_interface import IApexExchangeAdapter
from data_pipeline.historical_loader import ApexHistoricalLoader
from data_pipeline.live_feed import ApexLiveFeedEngine

class ApexPipelineCoordinator:
    """
    Module 1.8: Master Coordinator of the Data Layer.
    Orchestrates the entire synchronization lifecycle: validates assets,
    backfills historical caches, and spins up the live feed safely.
    """
    def __init__(self, exchange_adapter: IApexExchangeAdapter, loader: ApexHistoricalLoader):
        self.asset_mgr = ApexAssetManager()
        self.tf_mgr = ApexTimeframeManager()
        self.adapter = exchange_adapter
        self.loader = loader
        self.logger = logging.getLogger("ApexPipelineCoordinator")
        self.synchronized_symbols: List[str] = []

    def initialize_historical_sync(self, horizon_set: int, backfill_limit: int = 100) -> bool:
        """
        Step 1: Runs a sequential historical synchronization pass 
        for all registered assets across the chosen Horizon Set.
        """
        self.logger.info(f"Initializing historical sync sequence for Horizon Set {horizon_set}...")
        active_assets = self.asset_mgr.get_active_universe()
        target_timeframes = self.tf_mgr.get_horizon_timeframes(horizon_set)
        
        for symbol in active_assets:
            if not self.asset_mgr.is_allowed(symbol):
                self.logger.warning(f"Asset block intervened: {symbol} rejected from active pipeline pools.")
                continue
                
            for tf in target_timeframes:
                try:
                    norm_tf = self.tf_mgr.normalize_interval(tf)
                    self.logger.info(f"Backfilling {symbol} on {norm_tf} resolution frame...")
                    rows = self.loader.download_and_sync(symbol, norm_tf, limit=backfill_limit)
                    self.logger.info(f"[{symbol} - {tf}] Core backfill parsed. Synchronized entries: {rows}")
                except Exception as e:
                    self.logger.error(f"Failed sync pass step on asset cluster {symbol}: {str(e)}")
                    return False
                    
            self.synchronized_symbols.append(symbol)
        return True

    async def launch_live_stream_pipeline(self, live_feed_engine: ApexLiveFeedEngine, stream_cycles: int = 5):
        """
        Step 2: Hands over execution to the real-time non-blocking live feed stream handler.
        """
        if not self.synchronized_symbols:
            self.logger.warning("Live stream startup deferred: historical synchronization matrix holds no verified assets.")
            
        self.logger.info("Transitioning system pipeline into live data collection layout...")
        await live_feed_engine.start_simulated_stream(test_cycles=stream_cycles)
