class BaseStrategyProfile:
    """Defines the structural blueprint and risk boundaries for all modular strategy profiles."""
    def __init__(self, name, timeframe, risk_per_trade, target_rr, displacement_threshold, target_threshold):
        self.name = name
        self.timeframe = timeframe
        self.risk_per_trade = risk_per_trade
        self.target_rr = target_rr
        self.displacement_threshold = displacement_threshold
        self.target_threshold = target_threshold

    def serialize_profile(self):
        return {
            "profile_name": self.name,
            "timeframe": self.timeframe,
            "risk_allocation": self.risk_per_trade,
            "risk_reward_ratio": self.target_rr,
            "displacement_gate": self.displacement_threshold,
            "conviction_ceiling": self.target_threshold
        }
