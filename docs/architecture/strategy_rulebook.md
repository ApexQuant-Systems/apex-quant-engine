# 📘 APEX STRATEGY ENGINE RULEBOOK (v1.0.0 - LOCKED 🔒)

## 1. PURPOSE
To read the standardized states provided by the Market Language layer and evaluate multi-timeframe convergence rules to determine if a qualified trade layout candidate exists.

## 2. INPUT INTERFACE
* `MarketIntelligenceSnapshot` containing synchronized abstract timeframe states for layers `A`, `B`, and `C`.

## 3. OUTPUT INTERFACE
Must return a single, immutable `StrategyDecision` container containing exactly these fields:
* `symbol`: Standard string asset signature.
* `direction`: Unified structural trade directive (`BUY`, `SELL`, `WAIT`).
* `convergence_score`: Combined evaluation probability ranking convergence quality.
* `structural_anchor_levels`: Dict mapping explicit price markers needed for target assignment.

## 4. CORE RESPONSIBILITIES
* Enforce top-down timeframe alignment logic: **Timeframe A (Bias Vector) ➔ Timeframe B (Value Setup) ➔ Timeframe C (Execution Trigger)**.
* Short-circuit execution loops instantly by returning a `WAIT` token if any layer fails to validate alignment.
* Extract exact structural invalidation levels directly from layer records to use as calculation anchors.

## 5. STRICT RESTRICTIONS
* Must NEVER read raw candlestick fields. It can only evaluate abstract states.
* Must NEVER compute lot sizing, manage cash balances, track order states, or touch broker protocols.

## 6. VERIFICATION TESTS
* **Matrix Convergence Test:** Feed combinations of abstract states (e.g., A=Bullish, B=Pullback, C=Bullish) to verify deterministic matching against lookups.
* **Short-Circuit Verification:** Confirm that passing a single misaligned state layer drops execution flows to a `WAIT` token instantly.
