from strategies.base_profile import BaseStrategyProfile

class IntradaySniperProfile(BaseStrategyProfile):
    def __init__(self):
        super().__init__(
            name="INTRADAY_SNIPER",
            timeframe="1m",
            risk_per_trade=0.01,          # 1% Risk allocation
            target_rr=4.0,                # High asymmetry target
            displacement_threshold=1.5,   # Aggressive momentum validation
            target_threshold=70           # High conviction score gate
        )

class SwingVanguardProfile(BaseStrategyProfile):
    def __init__(self):
        super().__init__(
            name="SWING_VANGUARD",
            timeframe="1h",
            risk_per_trade=0.02,          # 2% Risk allocation due to higher timeframe stability
            target_rr=6.0,                # Macro expansion targets
            displacement_threshold=1.2,   # Smoother structural displacement gate
            target_threshold=65           # Moderate conviction consensus
        )
