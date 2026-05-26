import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_STATE_FILE = os.path.join(BASE_DIR, "storage", "portfolio_state.json")

class PortfolioRiskEngine:
    """Enforces strict risk architecture constraints across all active distributed workers."""
    def __init__(self, max_total_risk=0.02, max_positions=2):
        self.max_total_risk = max_total_risk  # 2% Maximum absolute portfolio risk heat
        self.max_positions = max_positions    # Maximum concurrent positions allowed across the system

    def evaluate_portfolio_heat(self, active_positions, requested_risk):
        current_allocated_risk = sum([pos['risk_capital'] for pos in active_positions.values()])
        total_projected_risk = current_allocated_risk + requested_risk

        if total_projected_risk > self.max_total_risk:
            return False, f"Risk Denied: Projected portfolio heat ({total_projected_risk*100:.1f}%) exceeds maximum limit ({self.max_total_risk*100:.1f}%)"
        
        if len(active_positions) >= self.max_positions:
            return False, f"Risk Denied: Active position count ({len(active_positions)}) sits at ceiling capacity ({self.max_positions})"
            
        return True, "Risk allocation authorized by core ledger."

class MasterOrchestrator:
    """The central nervous system governing risk distribution, state sync, and worker coordination."""
    def __init__(self):
        self.risk_engine = PortfolioRiskEngine()
        self.state_path = PORTFOLIO_STATE_FILE
        self._initialize_state_matrix()

    def _initialize_state_matrix(self):
        if not os.path.exists(os.path.dirname(self.state_path)):
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            
        if not os.path.exists(self.state_path):
            initial_state = {
                "system_status": "NOMINAL",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "active_positions": {}
            }
            with open(self.state_path, "w") as f:
                json.dump(initial_state, f, indent=4)

    def load_portfolio_state(self):
        with open(self.state_path, "r") as f:
            return json.load(f)

    def save_portfolio_state(self, state):
        state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=4)

    def request_execution_clearance(self, symbol, side, risk_amount):
        """Workers must execute this query to obtain state clearance before opening risk."""
        state = self.load_portfolio_state()
        active_positions = state["active_positions"]

        # Prevent duplicate exposure on the same asset token
        if symbol in active_positions:
            return {"status": "DENIED", "reason": f"Duplicate exposure attempt on active token {symbol}"}

        # Route validation to the mathematical portfolio risk engine
        passed, reason = self.risk_engine.evaluate_portfolio_heat(active_positions, risk_amount)
        
        if not passed:
            return {"status": "DENIED", "reason": reason}

        return {"status": "AUTHORIZED", "reason": "Clearance granted. Risk profile holds structural compliance."}

    def register_active_position(self, symbol, side, entry_price, risk_capital):
        state = self.load_portfolio_state()
        state["active_positions"][symbol] = {
            "side": side,
            "entry_price": entry_price,
            "risk_capital": risk_capital,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_portfolio_state(state)
        print(f"[+] [ORCHESTRATOR LOG] Registered active risk exposure for {symbol} on central state ledger.")

    def deregister_position(self, symbol):
        state = self.load_portfolio_state()
        if symbol in state["active_positions"]:
            del state["active_positions"][symbol]
            self.save_portfolio_state(state)
            print(f"[─] [ORCHESTRATOR LOG] Cleared asset exposure allocation for {symbol} from state matrix.")

if __name__ == "__main__":
    # Self-test confirmation matrix
    orchestrator = MasterOrchestrator()
    print("\n==================================================")
    print("   MASTER ORCHESTRATOR SYSTEM STATUS: NOMINAL     ")
    print("==================================================")
    
    # Simulation Audit 1: Test nominal risk tracking pass
    test_query = orchestrator.request_execution_clearance("SOLUSDT", "LONG", 0.01)
    print(f"[*] Simulation Run 1 (SOL 1% Risk Allocation Limit Check): {test_query['status']} -> {test_query['reason']}")
    
    # Registering mock position to state disk file to test core constraints
    orchestrator.register_active_position("SOLUSDT", "LONG", 130.50, 0.01)
    orchestrator.register_active_position("BTCUSDT", "SHORT", 76000.00, 0.01)
    
    # Simulation Audit 2: Attempting to trigger a 3rd position when cap is hit
    fail_query = orchestrator.request_execution_clearance("ETHUSDT", "LONG", 0.01)
    print(f"[*] Simulation Run 2 (ETH Allocation Limit Capacity Test) : {fail_query['status']} -> {fail_query['reason']}")
    
    # Resetting state ledger back to pristine room conditions
    orchestrator.deregister_position("SOLUSDT")
    orchestrator.deregister_position("BTCUSDT")
    print("==================================================\n")
