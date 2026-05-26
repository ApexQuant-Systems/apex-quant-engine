import pandas as pd

class ConcurrencyScoringEngine:
    def __init__(self, target_threshold=70):
        self.target_threshold = target_threshold

    def calculate_execution_score(self, regime: str, structural_signals: dict, displacement_metrics: dict) -> dict:
        """
        Synthesizes multiple operational layers into a single deterministic conviction matrix.
        Returns a payload containing the final score and an authorization flag.
        """
        score = 0
        break_detected = structural_signals.get("high_signal", False) or structural_signals.get("low_signal", False)
        
        # 1. Evaluate Environmental Foundation (Max Allocation: 30 Points)
        if regime in ["EXPANSION", "TRENDING"]:
            score += 30
        elif regime == "CONSOLIDATION":
            score += 10
        else: # UNDETERMINED / NEUTRAL
            score += 15

        # 2. Evaluate Structural Context (Max Allocation: 40 Points)
        if break_detected:
            score += 40

        # 3. Evaluate Momentum Confirmation (Max Allocation: 30 Points)
        if displacement_metrics.get("displacement", False):
            score += 30
        else:
            # Penalize the score heavily if structural breaks lack institutional backing
            if break_detected:
                score -= 20 

        # Ensure bounded boundaries [0, 100]
        final_score = max(0, min(100, score))
        authorized = final_score >= self.target_threshold

        return {
            "conviction_score": final_score,
            "execution_authorized": authorized,
            "threshold": self.target_threshold
        }
