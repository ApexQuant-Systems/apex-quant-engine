# 🔌 MARKET INTELLIGENCE ENGINE API & STATE MATRIX CONTRACT

The Market Intelligence Module abstracts away all structural parsing and candlestick analysis. It outputs a uniform state map, ensuring that downstream strategy engines never process raw price arrays directly.

## 1. IMMUTABLE SNAPSHOT DATA INTERFACE

```json
{
  "symbol": "BTCUSDT",
  "timestamp": "2026-06-20T22:15:00Z",
  "timeframe_states": {
    "HTF": {
      "trend": "BULLISH",
      "structure": "BOS_HIGH",
      "phase": "PULLBACK",
      "premium_discount": "DISCOUNT",
      "unmitigated_keyzones": [64200.0, 63800.0],
      "liquidity_pools": [69500.0, 71200.0],
      "confidence_score": 88.5
    },
    "MTF": {
      "trend": "BEARISH",
      "structure": "CONSOLIDATION",
      "phase": "PULLBACK",
      "premium_discount": "DISCOUNT",
      "unmitigated_keyzones": [64500.0],
      "liquidity_pools": [63100.0],
      "confidence_score": 75.0
    },
    "LTF": {
      "trend": "BEARISH",
      "structure": "CHOCH_LOW",
      "phase": "EXPANSION",
      "premium_discount": "PREMIUM",
      "unmitigated_keyzones": [],
      "liquidity_pools": [64150.0],
      "confidence_score": 60.0
    }
  }
}
2. VALUE STATE BOUNDARY MANIFESTS
trend: Enforces strict execution options matching ["BULLISH", "BEARISH", "NEUTRAL"].

structure: Maps breakouts via ["BOS_HIGH", "BOS_LOW", "CHOCH_HIGH", "CHOCH_LOW", "CONSOLIDATION"].

phase: Identifies market mechanics through ["EXPANSION", "PULLBACK", "ACCUMULATION", "DISTRIBUTION"].

premium_discount: Classifies regional positioning inside external ranges via ["PREMIUM", "EQUILIBRIUM", "DISCOUNT"].
