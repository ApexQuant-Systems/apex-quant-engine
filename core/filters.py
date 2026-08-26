# filename: core/filters.py
from dataclasses import dataclass
import time

@dataclass
class FilterResult:
    passed: bool
    reason: str

class FilterEngine:
    def __init__(self, max_spread: float = 0.05):
        self.max_spread = max_spread

    def validate_news(self, impact_level: str) -> FilterResult:
        """Blocks trades during HIGH impact news."""
        if impact_level == "HIGH":
            return FilterResult(False, "BLOCK: High impact news event.")
        return FilterResult(True, "PASS")

    def validate_spread(self, current_spread: float) -> FilterResult:
        """Blocks trades if spread exceeds threshold."""
        if current_spread > self.max_spread:
            return FilterResult(False, f"BLOCK: Spread too high ({current_spread})")
        return FilterResult(True, "PASS")

    def validate_session(self, current_hour: int, allowed_hours: list) -> FilterResult:
        """Blocks trades outside defined session."""
        if current_hour not in allowed_hours:
            return FilterResult(False, "BLOCK: Outside trading session.")
        return FilterResult(True, "PASS")
