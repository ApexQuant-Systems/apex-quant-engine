# 📘 APEX MARKET STATE CONTRACT (v1.0.0 - LOCKED 🔒)

## 1. PURPOSE
To convert continuous time-series price and volume inputs into a standardized, discrete description of market reality for any abstract timeframe layer ($Timeframe\_A, B, C$), completely insulating downstream modules from raw candlestick arrays.

## 2. INPUT INTERFACE
* Standardized, lookahead-free historical and streaming candle matrices containing native types: `[timestamp, open, high, low, close, volume]`.

## 3. OUTPUT INTERFACE
Must return a single, immutable `TimeframeState` container containing exactly these fields:
* `trend`: Dominant direction classification (`BULLISH`, `BEARISH`, `NEUTRAL`).
* `structure`: Key structural boundaries mapping (`BOS_HIGH`, `BOS_LOW`, `CHOCH_HIGH`, `CHOCH_LOW`, `CONSOLIDATION`).
* `phase`: Market behavior environment classification (`EXPANSION`, `PULLBACK`, `ACCUMULATION`, `DISTRIBUTION`).
* `keyzones`: List of floating-point prices tracking unmitigated structural coordinates.
* `liquidity_pools`: List of floating-point prices tracking major resting stop clusters.
* `strength`: Evidence-based normalized metric of market momentum and velocity.
* `confidence`: Quantitative confirmation weight representing data depth and pattern completion.
* `invalidated`: Boolean safety trip flag if an asset structure breaks mid-cycle.

## 4. CORE RESPONSIBILITIES
* Map directional energy and structural turning points sequentially up to index $t$.
* Guarantee **100% lookahead-free and repaint-free execution** across all data streams.
* Abstract away structural mathematics completely so downstream engines only see standardized states.

## 5. STRICT RESTRICTIONS
* Must NEVER possess knowledge of strategy states, portfolio balances, risk limits, or execution metrics.
* Must NEVER determine trade entries, calculate stop-loss coordinates, or issue order directions.

## 6. VERIFICATION TESTS
* **Deterministic Replay Test:** Processing identical historical arrays must return identical output states.
* **Lookahead Deface Test:** Shifting or truncating data arrays past index $t$ must alter states down the line without leaking future information backward.
