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
        # FIXED: Using timezone-aware UTC to prevent Python deprecation warnings
        print(f"[{datetime.datetime.now(datetime.timezone.utc)}] SYSTEM BOOT: Apex Quant Orchestrator Initialized.")
        
        # Initialize all institutional modules
        self.data_engine = CryptoDataIngestion(exchange_id='binance')
        self.regime_engine = RegimeEngine(adx_period=14, adx_threshold=25)
        self.structure_engine = StructureEngine(lookback=2, lookforward=2)
        self.scoring_engine = ScoringEngine()
        
        # 1% Risk Firewall starting on a hypothetical $10,000 Portfolio
        self.portfolio_balance = 10000.0
        self.risk_firewall = InstitutionalRiskFirewall(account_balance=self.portfolio_balance, base_risk_pct=0.01)
        
        # --- POSITION STATE MANAGER (SYSTEM MEMORY) ---
        self.in_position = False
        self.active_trade = {
            "size": 0.0,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0
        }
        
    def manage_open_position(self, current_live_price):
        """Monitors the active trade and closes it if structural limits are hit."""
        print(f" -> [STATE MANAGER] Holding ACTIVE LONG: {self.active_trade['size']} BTC")
        print(f" -> [TRACKING] Current: ${current_live_price:.2f} | Target: ${self.active_trade['take_profit']:.2f} | Stop: ${self.active_trade['stop_loss']:.2f}")
        
        if current_live_price >= self.active_trade['take_profit']:
            profit = (self.active_trade['take_profit'] - self.active_trade['entry_price']) * self.active_trade['size']
            self.portfolio_balance += profit
            print(f"\n >>> [TARGET HIT] Trade Closed in PROFIT: +${profit:.2f} <<<")
            print(f" >>> New Portfolio Balance: ${self.portfolio_balance:.2f} <<<\n")
            self.in_position = False # Free up the system for the next trade
            
        elif current_live_price <= self.active_trade['stop_loss']:
            loss = (self.active_trade['entry_price'] - self.active_trade['stop_loss']) * self.active_trade['size']
            self.portfolio_balance -= loss
            print(f"\n >>> [STOP LOSS HIT] Trade Closed in LOSS: -${loss:.2f} <<<")
            print(f" >>> New Portfolio Balance: ${self.portfolio_balance:.2f} <<<\n")
            self.in_position = False
            
        else:
            print(" -> [HOLDING] Price is within operational bounds. Waiting for resolution.")

    def run_cycle(self):
        print(f"\n[{datetime.datetime.now(datetime.timezone.utc)}] Initiating Matrix Cycle...")
        
        try:
            # STEP 1: INGESTION
            print(" -> Pinging Binance API for latest OHLCV arrays...")
            recent_start = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
            df = self.data_engine.fetch_historical_candles('BTC/USDT', '1h', recent_start)
            
            if df is None or df.empty:
                print(" -> [ERROR] Data extraction failed. Aborting cycle.")
                return

            latest_closed_candle = df.iloc[-2] # The last fully closed 1H candle
            current_live_price = df.iloc[-1]['close'] # The actively ticking price right now

            # --- MEMORY CHECK: ARE WE ALREADY IN A TRADE? ---
            if self.in_position:
                self.manage_open_position(current_live_price)
                return # Abort cycle here. We do not look for new setups while holding a trade.

            # STEP 2: REGIME FILTER
            print(" -> Scanning Market Environment...")
            df = self.regime_engine.classify_market_regime(df)
            
            # STEP 3: STRUCTURE ALIGNMENT
            df = self.structure_engine.detect_swings(df)
            
            # STEP 4: PROBABILITY SCORING
            df = self.scoring_engine.score_displacement(df)
            
            # Update latest state after processing
            latest_closed_state = df.iloc[-2] 
            
            print(f" -> Market State [BTC/USDT]: Price=${latest_closed_state['close']:.2f} | Regime={latest_closed_state.get('Regime_Status', 'UNKNOWN')} | Score={latest_closed_state.get('setup_score', 0)}")
            
            # THE HARD LOGIC GATE
            if not latest_closed_state.get('Trade_Authorized', False):
                print(" -> [LOCKED] No A+ setup detected on the current candle. Standing by.")
                return
            
            # STEP 5: RISK GOVERNANCE & TRADE EXECUTION
            print(" -> [ALERT] Setup Authorized! Calculating constraints...")
            
            # Update firewall with live balance before sizing
            self.risk_firewall.account_balance = self.portfolio_balance
            
            entry_price = latest_closed_state['close']
            stop_loss = entry_price * 0.98 # Simulated 2% structural stop
            
            # Ensure the absolute 1:4 Reward Rule
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + (risk_distance * 4.0) 
            
            size = self.risk_firewall.calculate_protected_size(
                entry_price=entry_price, stop_loss=stop_loss,
                estimated_slippage_pct=0.0005, current_correlation=0.0, active_exposure=False
            )
            
            if size > 0:
                print(f" -> [FIREWALL PASSED] DISPATCHING PAYLOAD: BUY {size} BTC/USDT at ${entry_price:.2f}")
                # LOCK THE MEMORY STATE
                self.in_position = True
                self.active_trade = {
                    "size": size,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit
                }
            else:
                print(" -> [REJECTED] Risk Firewall blocked the execution.")

        except Exception as e:
            print(f" -> [SYSTEM FAULT] Matrix cycle interrupted: {e}")

    def start_autonomous_loop(self, interval_seconds=900):
        print(">>> COMMENCING AUTONOMOUS OPERATIONS WITH MEMORY STATE MANAGEMENT <<<")
        try:
            while True:
                self.run_cycle()
                print(f"[{datetime.datetime.now(datetime.timezone.utc)}] Cycle complete. System entering hibernation for {interval_seconds} seconds.")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n>>> MANUAL OVERRIDE DETECTED. SHUTTING DOWN ENGINES. <<<")

if __name__ == "__main__":
    master_node = ApexQuantOrchestrator()
    # Running on a 15-second loop for immediate terminal testing
    master_node.start_autonomous_loop(interval_seconds=15)
