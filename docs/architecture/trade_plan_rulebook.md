# 📘 APEX TRADE PLAN RULEBOOK (v1.0.0 - LOCKED 🔒)

## 1. PURPOSE
To convert valid, aligned strategy decisions into an explicit, geometric trade execution profile based on structural market invalidation coordinates.

## 2. INPUT INTERFACE
* Standardized `StrategyDecision` token and the immediate structural price coordinates passed from upper layers.

## 3. OUTPUT INTERFACE
Must return a single, immutable `TradePlan` container containing exactly these fields:
* `symbol`, `direction`, `entry_price`, `stop_loss`, `take_profit`.
* `risk_reward_ratio`: Floating-point representation of reward potential divided by risk distance.
* `is_valid`: Boolean gate confirming structural minimum metrics are achieved.

## 4. CORE RESPONSIBILITIES
* Map execution entries and hard stop-loss targets directly to structural invalidation coordinates (e.g., sweep wicks or structure origins).
* Compute reward distances to target zones and verify them against the configurable `MINIMUM_ACCEPTABLE_REWARD_RISK` ceiling parameter.
* Flag layouts as invalid if the calculated structural reward-to-risk matrix falls below the baseline filter profile.

## 5. STRICT RESTRICTIONS
* Must NEVER evaluate macro trend states, alter directional intent, or compute portfolio capitalization parameters.
* Must NEVER alter risk percentages or process network communication states.

## 6. VERIFICATION TESTS
* **Geometric Guard Test:** Pass inputs where target boundaries produce a 1:3.9 ratio; verify that `is_valid` resolves to `False`.
* **Zero Division Protection:** Verify that passing identical entry and stop-loss coordinates handles the error cleanly instead of crashing the process loop.
