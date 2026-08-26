from core_vNext.structure.swing_engine import StructuralSwing, SwingType

class TrailingEngine:
    """
    Enforces monotonic MTF structural trailing invariants.
    """
    def __init__(self):
        pass

    def evaluate_trail(self, current_sl: float, side: str, latest_swing: StructuralSwing) -> float:
        """
        Monotonic trailing rule. Returns the new SL price.
        Rule 1: Never loosen.
        Rule 2: Confirmed structure only (latest_swing is inherently confirmed).
        """
        if not latest_swing:
            return current_sl

        if side == 'LONG':
            # Trail below latest confirmed higher low
            if latest_swing.type == SwingType.LOW:
                if latest_swing.price > current_sl:
                    return latest_swing.price
        elif side == 'SHORT':
            # Trail above latest confirmed lower high
            if latest_swing.type == SwingType.HIGH:
                if latest_swing.price < current_sl:
                    return latest_swing.price

        return current_sl
