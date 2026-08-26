import os
import sys
import asyncio
import time

# Append workspace root directory for clean cross-module importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from execution.demo_broker_v4 import ApexStateBroker

class ApexRiskEngine:
    """
    🛰️ APEX RISK CONTROL CORE: STAGE H5
    Enforces structural account rules and trading guardrails before order dispatch.
    """
    def __init__(self, max_open_positions: int = 3, max_qty_per_trade: float = 0.05):
        self.max_positions = max_open_positions
        self.max_qty = max_qty_per_trade
        self.current_active_positions = 0
        self.system_cooldown_active = False

    def validate_signal_risk(self, symbol: str, side: str, quantity: float) -> tuple[bool, str]:
        """Evaluates an incoming signal against strict institutional constraints."""
        if self.system_cooldown_active:
            return False, "RISK_REJECTION: Global system cooldown or kill-switch engaged."
            
        if self.current_active_positions >= self.max_positions and side.upper() == "BUY":
            return False, f"RISK_REJECTION: Open position ceiling ({self.max_positions}) reached."
            
        if quantity > self.max_qty:
            return False, f"RISK_REJECTION: Trade quantity {quantity} exceeds single-allocation cap ({self.max_qty})."
            
        return True, "RISK_CLEARED: Signal within safe performance boundaries."

class RiskAwareExecutionRouter:
    """
    🛰️ APEX ROUTING FABRIC: STAGE H1
    Orchestrates signal reception, risk gate checks, and asset broker handshakes.
    """
    def __init__(self):
        self.risk_core = ApexRiskEngine(max_open_positions=2, max_qty_per_trade=0.02)
        self.broker = ApexStateBroker()

    async def route_strategy_signal(self, signal_payload: dict):
        print(f"\n📡 [SIGNAL RECEIVED] Origin: {signal_payload['source']} | Pattern: {signal_payload['setup']}")
        
        symbol = signal_payload["symbol"]
        side = signal_payload["side"]
        qty = signal_payload["quantity"]
        
        # Pass the message down into the risk checking core
        is_approved, risk_message = self.risk_core.validate_signal_risk(symbol, side, qty)
        
        if not is_approved:
            print(f"🚨 [RISK INTERCEPTED] {risk_message}")
            print("  └── Execution pipeline halted for this frame.")
            return
            
        print(f"🛡️  [RISK CLEARED] Dispatching validated order routing token to broker lines...")
        
        # Increment tracking state to mimic live context allocation
        if side.upper() == "BUY":
            self.risk_core.current_active_positions += 1
            
        # Execute the transaction through our verified async testnet broker
        order_receipt = await self.broker.submit_resting_limit_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=signal_payload["target_price"]
        )
        
        if order_receipt.get("orderId"):
            print(f"🟢 [ROUTER METRIC] Trade successfully deployed to Sandbox. Exchange ID: {order_receipt.get('orderId')}")
        else:
            print("❌ [ROUTER FAULT] Broker layout failed to execute approved transaction payload.")

async def run_router_gauntlet():
    print("=====================================================================")
    print(" 🛰️  APEX INTEGRATION ROUTER: TESTING RISK ENGINE CONTROL GATES")
    print("=====================================================================")
    
    router = RiskAwareExecutionRouter()
    
    # --- TRIAL 1: Safe Intraday Signal from Frozen SET 4 Framework ---
    valid_signal = {
        "source": "APEX_SET_4_INTRADAY",
        "setup": "15M_OB_LIQUIDITY_SWEEP",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,         # Safely under our 0.02 max cap rule
        "target_price": 60000.0
    }
    await router.route_strategy_signal(valid_signal)
    
    await asyncio.sleep(2.0)
    
    # --- TRIAL 2: Malformed Macro Size Signal that Violates Exposure Rules ---
    rogue_signal = {
        "source": "APEX_SET_1_MACRO",
        "setup": "1D_FAIR_VALUE_GAP",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.09,         # BREACHES THE 0.02 SINGLE QUANTITY RISK LIMIT
        "target_price": 60000.0
    }
    await router.route_strategy_signal(rogue_signal)
    
    # Clean up the test environment by executing our atomic panic switch to clear the book
    print("\n⚡ Running automated environment clean-up...")
    await router.broker.cancel_all_open_orders(symbol="BTCUSDT")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_router_gauntlet())
