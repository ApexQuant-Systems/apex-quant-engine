# APEX QUANT SYSTEM: MASTER RULEBOOK (V1 - CRYPTO CORE)

## 1. SYSTEM PHILOSOPHY
- Target Assets: BTC/USDT, ETH/USDT (Maximum liquidity, 24/7/365 execution).
- Strategy: Multi-Timeframe (HTF -> MTF -> LTF) Structural trend following.
- Execution Rule: No discretionary overrides. If the math does not trigger, the bot does not trade.

## 2. THE MATHEMATICAL TRANSLATION
No subjective chart reading. All concepts are strictly defined by code:
- Swing High: A candle high that is strictly greater than the 2 candles before it AND the 2 candles after it.
- FVG (Fair Value Gap): A 3-candle sequence where Candle 1 High < Candle 3 Low (Bullish) or Candle 1 Low > Candle 3 High (Bearish).
- BOS (Break of Structure): A structural candle CLOSE beyond the last mathematical Swing High/Low.

## 3. DYNAMIC RISK FIREWALL
- Absolute Risk: Maximum 1% of total portfolio capital per trade.
- Stop Loss: Dynamically calculated at 1.5x the 14-period Average True Range (ATR).
- Invalidation: If the MTF structure closes below the HTF swing point, the system forces a market exit immediately.
