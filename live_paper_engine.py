import asyncio
import json
import os
import sys
import urllib.request
import pandas as pd
from datetime import datetime, timedelta
from collections import deque

# Absolute path configuration matrix
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from infrastructure.logger import QuantLogger
from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from structure_engine.displacement_detector import DisplacementEngine
from core.scoring_engine import ConcurrencyScoringEngine
from execution.paper_orders import PaperExecutionEngine
from storage.trade_journal import TradeJournalDB

HEARTBEAT_FILE = os.path.join(BASE_DIR, "infrastructure", "heartbeat.txt")
FORCE_TEST_TRIGGER = False 

class AssetWorker:
    """Manages an isolated memory layer and intelligence cascade for a specific asset token."""
    def __init__(self, symbol, base_broker, base_db, logger):
        self.symbol = symbol
        self.broker = base_broker
        self.db = base_db
        self.log = logger
        self.history = deque(maxlen=50)
        self.current_candle = None
        self.active_db_id = None
        
        # Instantiate dedicated intelligence modules to safeguard tracking states
        self.regime_engine = RegimeEngine()
        self.structure_engine = StructureEngine(lookback=5)
        self.displacement_engine = DisplacementEngine(lookback=5, threshold_multiplier=1.5)
        self.scoring_engine = ConcurrencyScoringEngine(target_threshold=70)

    def bootstrap_memory(self):
        self.log.log(f"[*] [{self.symbol}] Seeding state memory matrix via historical REST API...")
        rest_url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol}&interval=1m&limit=50"
        try:
            req = urllib.request.Request(rest_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                klines = json.loads(response.read().decode())
                for k in klines[:-1]:  
                    self.history.append({
                        "start_time": datetime.fromtimestamp(k[0] / 1000.0).replace(second=0, microsecond=0),
                        "open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4])
                    })
            self.log.log(f"[+] [{self.symbol}] Warm-up complete. Hydrated {len(self.history)} candles.")
        except Exception as e:
            self.log.error(f"[-] [{self.symbol}] Historical bootstrap aborted: {e}")

    def init_candle(self, price, timestamp):
        return {
            "start_time": timestamp.replace(second=0, microsecond=0),
            "open": price, "high": price, "low": price, "close": price
        }

class MultiAssetExecutionEngine:
    def __init__(self, symbols):
        self.symbols = symbols
        self.log = QuantLogger()
        self.db = TradeJournalDB()
        self.broker = PaperExecutionEngine(initial_balance=10000.0)
        self.candle_duration = timedelta(minutes=1)
        
        # Initialize specialized processing blocks per targeted asset
        self.workers = {sym: AssetWorker(sym, self.broker, self.db, self.log) for sym in self.symbols}
        
        for worker in self.workers.values():
            worker.bootstrap_memory()
            
    def pulse_heartbeat(self):
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(datetime.now().timestamp()))
        except Exception as e:
            print(f"Failed to record system pulse: {e}")

    async def run_symbol_worker(self, symbol):
        worker = self.workers[symbol]
        url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@ticker"
        
        import websockets
        while True:
            try:
                async with websockets.connect(url) as ws:
                    self.log.log(f"[+] [SOCKET CONNECTED] Active market data pipeline open for {symbol}")
                    
                    while True:
                        raw_data = await ws.recv()
                        data = json.loads(raw_data)
                        
                        price = float(data.get('c', 0))
                        tick_time = datetime.fromtimestamp(data.get('E', 0) / 1000.0)
                        
                        if not worker.current_candle:
                            worker.current_candle = worker.init_candle(price, tick_time)
                            
                        # Process real-time boundary updates across open positions
                        if self.broker.active_position and self.broker.active_position.get('symbol') == symbol:
                            exit_update = self.broker.process_market_tick(price, tick_time)
                            if exit_update and worker.active_db_id is not None:
                                self.db.write_trade_exit(
                                    trade_id=worker.active_db_id, exit_price=price,
                                    pnl=exit_update['pnl'], reason=exit_update['reason'], timestamp=tick_time
                                )
                                self.log.log(f"\n💾 [{symbol}] [DATABASE SYNC] Trade ID {worker.active_db_id} committed to disk.")
                                self.log.log(f"💵 [{symbol}] [TRADE CLOSED] {exit_update['reason']} | Exit: ${price:.2f} | PnL: ${exit_update['pnl']:.2f}\n")
                                worker.active_db_id = None

                        # Handle minute boundary rollover transformations
                        if tick_time >= worker.current_candle["start_time"] + self.candle_duration:
                            c = worker.current_candle
                            worker.history.append(c)
                            
                            if len(worker.history) >= 20:
                                df_state = pd.DataFrame(list(worker.history))
                                
                                # Process metrics through the analytics stack
                                df_analyzed = worker.regime_engine.classify_market_regime(df_state)
                                current_regime = df_analyzed.iloc[-1].get('regime', 'UNDETERMINED')
                                
                                df_structured = worker.structure_engine.detect_swings(df_analyzed)
                                struct_signals = {
                                    "high_signal": bool(df_structured.iloc[-1].get('Swing_High', False)),
                                    "low_signal": bool(df_structured.iloc[-1].get('Swing_Low', False))
                                }
                                
                                disp_metrics = worker.displacement_engine.validate_displacement(df_structured)
                                score_payload = worker.scoring_engine.calculate_execution_score(
                                    current_regime, struct_signals, disp_metrics
                                )
                                
                                authorized = score_payload["execution_authorized"]
                                
                                # Filter logging tracking outputs
                                if authorized and not self.broker.active_position:
                                    side = "LONG" if struct_signals["low_signal"] else "SHORT"
                                    simulated_atr = (df_structured['high'] - df_structured['low']).tail(5).mean()
                                    
                                    order_placed = self.broker.execute_virtual_order(
                                        side=side, entry_price=price, current_atr=simulated_atr, timestamp=tick_time
                                    )
                                    if order_placed:
                                        self.broker.active_position['symbol'] = symbol # Tag position
                                        pos = self.broker.active_position
                                        self.log.log(f"🔥 [{symbol}] [VIRTUAL TRADE PLACED] {side} | Entry: ${price:.2f} | SL: ${pos['sl']:.2f}")
                                        
                                        worker.active_db_id = self.db.write_trade_entry(
                                            side=side, entry_price=price, sl=pos['sl'], tp=pos['tp'],
                                            size=pos['size'], risk_capital=pos['risk_capital'],
                                            regime=current_regime, ratio=disp_metrics['ratio'],
                                            score=score_payload["conviction_score"], timestamp=tick_time
                                        )
                                
                            worker.current_candle = worker.init_candle(price, tick_time)
                        else:
                            worker.current_candle["high"] = max(worker.current_candle["high"], price)
                            worker.current_candle["low"] = min(worker.current_candle["low"], price)
                            worker.current_candle["close"] = price
                            
                        self.pulse_heartbeat()
                        
            except Exception as e:
                self.log.error(f"[-] [{symbol}] Transport connection loss detected: {e}")
                await asyncio.sleep(5)

    def start_main_pipeline(self):
        self.log.log("\n==================================================")
        self.log.log("   SYSTEM ACTIVE: MULTI-ASSET ASYMMETRICAL SCOUT ")
        self.log.log("==================================================")
        
        loop = asyncio.get_event_loop()
        # Orchestrate processing loops for all configured assets simultaneously
        tasks = [self.run_symbol_worker(sym) for sym in self.symbols]
        loop.run_until_complete(asyncio.gather(*tasks))

if __name__ == "__main__":
    target_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    master_engine = MultiAssetExecutionEngine(target_assets)
    try:
        master_engine.start_main_pipeline()
    except KeyboardInterrupt:
        print("\n[!] Multi-asset matrix safely parked by systems operator.")
        sys.exit(0)
