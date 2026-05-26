from datetime import datetime

class PaperExecutionEngine:
    def __init__(self, initial_balance=10000.0, risk_reward_ratio=4.0, risk_per_trade=0.01):
        self.balance = initial_balance
        self.cash = initial_balance
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade 
        
        self.active_position = None  
        self.trade_history = []

    def process_market_tick(self, active_price: float, timestamp: datetime) -> dict:
        """
        Mark-to-Market Loop: Evaluates active virtual position barriers against the live price tick.
        """
        if not self.active_position:
            return None

        pos = self.active_position
        pnl = 0.0
        closed = False
        exit_reason = ""

        if pos["side"] == "LONG":
            if active_price <= pos["sl"]:
                closed = True
                exit_reason = "STOP_LOSS"
                pnl = (pos["sl"] - pos["entry_price"]) * pos["size"]
            elif active_price >= pos["tp"]:
                closed = True
                exit_reason = "TAKE_PROFIT"
                pnl = (pos["tp"] - pos["entry_price"]) * pos["size"]
        
        elif pos["side"] == "SHORT":
            if active_price >= pos["sl"]:
                closed = True
                exit_reason = "STOP_LOSS"
                pnl = (pos["entry_price"] - pos["sl"]) * pos["size"]
            elif active_price <= pos["tp"]:
                closed = True
                exit_reason = "TAKE_PROFIT"
                pnl = (pos["entry_price"] - pos["tp"]) * pos["size"]

        if closed:
            if exit_reason == "TAKE_PROFIT":
                self.cash += pnl + pos["risk_capital"]
            else:
                self.cash += (pos["risk_capital"] + pnl) # Deducts loss smoothly from escrowed risk capital
            
            completed_trade = {
                "entry_time": pos["entry_time"],
                "exit_time": timestamp,
                "side": pos["side"],
                "entry_price": pos["entry_price"],
                "exit_price": active_price,
                "pnl": pnl,
                "reason": exit_reason
            }
            self.trade_history.append(completed_trade)
            self.balance = self.cash
            self.active_position = None
            
            return completed_trade

        return None

    def execute_virtual_order(self, side: str, entry_price: float, current_atr: float, timestamp: datetime) -> bool:
        """
        Assembles and maps a new risk-defined virtual position into operational memory.
        """
        if self.active_position:
            return False

        risk_amount = self.balance * self.risk_per_trade
        stop_distance = current_atr if current_atr > 0 else (entry_price * 0.005)
        
        if side == "LONG":
            sl = entry_price - stop_distance
            tp = entry_price + (stop_distance * self.risk_reward_ratio)
        else: 
            sl = entry_price + stop_distance
            tp = entry_price - (stop_distance * self.risk_reward_ratio)

        size = risk_amount / stop_distance
        
        self.active_position = {
            "entry_time": timestamp,
            "side": side,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "size": size,
            "risk_capital": risk_amount
        }
        
        self.cash -= risk_amount
        return True
