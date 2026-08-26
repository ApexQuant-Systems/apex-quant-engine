# 📘 APEX OS MARKET LANGUAGE ENGINE RULEBOOK (v1.0.0 - LOCKED 🔒)

This framework sets the mandatory logic for translating raw chronological pricing arrays into abstract `TimeframeState` contract tokens. All future mathematical modules must strictly implement these conceptual definitions.

---

## 1. THE TREND ENGINE SPECIFICATION
The Trend component determines the dominant market direction for any given timeframe layer ($Timeframe\_A, B, C$) over an evidence-driven observation window.

### A. Trend States
* **BULLISH:** Price exhibits clean structural drift above the dynamic value baseline, with higher-scale market structure consistently validating demand boundaries.
* **BEARISH:** Price exhibits clear downward pressure beneath the dynamic value baseline, with lower-scale market structure breaking support regions.
* **NEUTRAL:** Price is compressed inside a tightly bound horizontal band, fluctuating across the dynamic value baseline without direction.

### B. Input/Output Matrix
* **Required Input:** Standardized data frame rows up to the current index $t$.
* **Immutable Output:** `MarketTrend` Enum matching `[BULLISH, BEARISH, NEUTRAL]`.

---

## 2. THE STRUCTURE ENGINE SPECIFICATION
The Structure component maps turning points (swing extremes) and tracks market breakouts while strictly avoiding lookahead errors.

### A. Swing Pivot Invalidation Laws
* **Swing High ($S_H$):** A local peak at index $i$ is valid if and only if the high price at index $i$ is the absolute highest value within the window $[i - N_{Left}, i + N_{Right}]$.
* **Swing Low ($S_L$):** A local trough at index $i$ is valid if and only if the low price at index $i$ is the absolute lowest value within the window $[i - N_{Left}, i + N_{Right}]$.
* *Execution Lag Constraint:* In live operations, a pivot point formed at bar $t$ cannot be registered by the engine until index $t + N_{Right}$ has officially closed.

### B. Break of Structure (BOS) vs. Change of Character (CHOCH)
* **BOS (Break of Structure):** Triggered when the current candle *body close* extends beyond the most recent confirmed swing extreme in the direction of the dominant trend.
* **CHOCH (Change of Character):** Triggered when the current candle *body close* breaks the final swing extreme opposite to the primary dominant trend, signaling an early structural reversal.
* *Wick Exclusion Rule:* Punctures where only the candle *wick* crosses a swing high or low do not qualify as structural breaks. They are passed directly to the Liquidity Engine.

---

## 3. THE KEYZONE ENGINE SPECIFICATION
The Keyzone component isolates unmitigated institutional value zones where order entry footprints remain unfilled.

### A. Structural Value Regions
* **Imbalance Keyzones (Fair Value Gaps):** A three-candle geometric formation where a structural vacancy exists between the low of Candle 1 and the high of Candle 3.
* **Mitigation Constraints:** A keyzone is classified as *active* if current price action has not revisited or pierced its boundary lines. The instant price breaks or fills the boundary, the zone is flagged as *mitigated* and removed from active tracking.

---

## 4. THE LIQUIDITY ENGINE SPECIFICATION
The Liquidity component monitors the positioning of market stops and maps predatory sweep events.

### A. Liquidity Targets & Pools
* **Equal Highs / Equal Lows (EQH/EQL):** Structural ranges where multiple historical wicks terminate at nearly identical price coordinates ($\pm$ a configurable precision threshold). This signals clustered stop-loss resting orders.
* **Predatory Sweeps:** Registered when a candle wick punctures a validated liquidity pool or swing extreme, but the candle body fails to close beyond it and snaps back inside the range.

---

## 5. THE PHASE ENGINE SPECIFICATION
The Phase component defines the market environment type, allowing the Strategy Module to adjust its confirmation parameters.

### A. Environment Categorization
* **EXPANSION:** Price breaks out out of an established range with a high-velocity momentum signature.
* **PULLBACK:** Price trades in a counter-trend correction toward an unmitigated premium or discount keyzone.
* **ACCUMULATION / DISTRIBUTION:** Price is contained within horizontal trading ranges, establishing a balance area before the next expansion phase.

---

## 6. EXTENSION METRICS SPECIFICATION
To ensure the Strategy Engine can filter out low-probability environments, each timeframe snapshot must populate three quantitative extension metrics:

### A. Strength
* A rolling momentum and volatility velocity calculation (e.g., Average True Range or Volume weightings) used to rank trend urgency.

### B. Invalidated
* An explicit safety flag that trips to `True` if a sudden, high-volatility structural break invalidates the current bias before the next state calculation.

### C. Quality Score
* A composite rating from `0.0` to `10.0` that tracks pattern completion quality, calculated by assessing zone depth, mitigation history, and timeframe alignment.
