import time
import datetime
import sys
import os

# Ensure the Python engine can locate all modular folders from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the 4 Pillars of the Apex Architecture
from data.data_handler import CryptoDataIngestion
from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from core.scoring_engine import ScoringEngine
from risk_engine.order_sizer import InstitutionalRiskFirewall

class ApexQuantOrchestrator:
    def __init__(self):
        print(f"[{datetime.datetime.now()}] SYSTEM BOOT: Apex Quant Orchestrator Initialized.")
        
        # Initialize all institutional modules
        self.data_engine = CryptoDataIngestion(exchange_id='binance')
        self.regime_engine = RegimeEngine(adx_period=14, adx_threshold=25)
        self.structure_engine = StructureEngine(lookback=2, lookforward=2)
        self.scoring_engine = ScoringEngine()
        
        # 1% Risk Firewall on a hypothetical $10,000 Portfolio
        self.risk_firewall = InstitutionalRiskFirewall(account_balance=10000.0, base_risk_pct=0.01)
        
        self.active_positions = 0
        
    def run_cycle(self):
        print(f"\n[{datetime.datetime.now()}] Initiating Matrix Cycle...")
        
        try:
            # STEP 1: INGESTION
            print(" -> Pinging Binance API for latest OHLCV arrays...")
            # Fetch a short 5-day window to keep the live loop lightning fast, 
            # ensuring enough data for the 20-period moving averages to calculate.
            recent_start = (datetime.datetime.utcnow() - datetime.timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
            df = self.data_engine.fetch_historical_candles('BTC/USDT', '1h', recent_start)
            
            if df is None or df.empty:
                print(" -> [ERROR] Data extraction failed. Aborting cycle.")
                return

            # STEP 2: REGIME FILTER
            print(" -> Running Regime Classification (ADX)...")
            df = self.regime_engine.classify_market_regime(df)
            
            # STEP 3: STRUCTURE ALIGNMENT
            print(" -> Mapping structural swing points...")
            df = self.structure_engine.detect_swings(df)
            
            # STEP 4: PROBABILITY SCORING
            print(" -> Scoring displacement and volume footprints...")
            df = self.scoring_engine.score_displacement(df)
            
            # Analyze the last fully closed candle (index -2 because index -1 is currently forming)
            latest_candle = df.iloc[-2] 
            
            print(f" -> Current Market State [BTC/USDT]: Price=${latest_candle['close']:.2f} | Regime={latest_candle.get('Regime_Status', 'UNKNOWN')} | Score={latest_candle.get('setup_score', 0)}")
            
            # THE HARD LOGIC GATE
            if not latest_candle.get('Trade_Authorized', False):
                print(" -> [LOCKED] No A+ setup detected on the current candle. Standing by.")
                return
            
            # STEP 5: RISK GOVERNANCE
            print(" -> [ALERT] Setup Authorized! Running Risk Firewall constraints...")
            # For this live test, we simulate a structural stop loss 2% below the entry
            entry_price = latest_candle['close']
            stop_loss = entry_price * 0.98 
            
            size = self.risk_firewall.calculate_protected_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                estimated_slippage_pct=0.0005,
                current_correlation=0.0,
                active_exposure=False
            )
            
            if size <= 0:
                print(" -> [REJECTED] Risk Firewall blocked the execution (Slippage/Risk limits exceeded).")
                return
            
            # STEP 6: EXECUTION
            print(f" -> [FIREWALL PASSED] DISPATCHING PAYLOAD TO BROKER: BUY {size} BTC/USDT")
            self.active_positions += 1

        except Exception as e:
            print(f" -> [SYSTEM FAULT] Matrix cycle interrupted: {e}")

    def start_autonomous_loop(self, interval_seconds=900):
        print(">>> COMMENCING AUTONOMOUS OPERATIONS <<<")
        try:
            while True:
                self.run_cycle()
                print(f"[{datetime.datetime.now()}] Cycle complete. System entering hibernation for {interval_seconds} seconds.")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n>>> MANUAL OVERRIDE DETECTED. SHUTTING DOWN ENGINES. <<<")

if __name__ == "__main__":
    master_node = ApexQuantOrchestrator()
    # Running on a 15-second loop for immediate terminal testing
    master_node.start_autonomous_loop(interval_seconds=15)

