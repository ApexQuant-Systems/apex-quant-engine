from enum import Enum
from typing import Optional
from core_vNext.execution.order_intent import OrderIntent

class StrategyState(Enum):
    IDLE = 1
    HTF_BIAS_CONFIRMED = 2
    WAITING_HTF_CONTEXT = 3
    AWAITING_MTF_ALIGNMENT = 4
    MTF_ALIGNED = 5
    WAITING_MTF_KEYZONE = 6
    MTF_KEYZONE_TOUCHED = 7
    AWAITING_LTF_ENTRY = 8
    LTF_ENTRY_CONFIRMED = 9
    RISK_APPROVED = 10
    ORDER_SUBMITTED = 11
    POSITION_ACTIVE = 12
    MTF_TRAILING = 13
    EXIT = 14
    POST_TRADE = 15
    COOLDOWN = 16

class StateMachine:
    """
    Finite State Machine managing the lifecycle of a strategy setup.
    """
    def __init__(self, asset: str, timeframe_set: str):
        self.asset = asset
        self.timeframe_set = timeframe_set
        self.state = StrategyState.IDLE
        self.active_intent: Optional[OrderIntent] = None

    def transition_to(self, new_state: StrategyState):
        # Note: In a production system, valid transition matrices would be enforced here.
        # print(f"[{self.asset} {self.timeframe_set}] State Transition: {self.state.name} -> {new_state.name}")
        self.state = new_state

    def reset(self):
        self.state = StrategyState.IDLE
        self.active_intent = None
