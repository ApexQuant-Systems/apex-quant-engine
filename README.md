# Apex Quant Systems: Distributed Research & Execution Framework (v1.0)

A highly decoupled, fault-tolerant, and modular multi-asset quantitative trading infrastructure engine engineered for real-time WebSocket ingestion, multi-timeframe candle synthesis, centralized risk governance, and isolated high-fidelity simulation testing.

---

## 🛠️ System Architecture

The platform implements a decoupled, universal hardware chassis model. The underlying network infrastructure, state machines, and data streams remain entirely frozen, while alpha strategy logic and timeframe configurations shift dynamically via hot-swappable parameter cartridges.

```text
==========================================================================
                 [ CENTRAL AUTONOMOUS SUPERVISOR DAEMON ]
              (Monitors Vitality Registers / OS Auto-Heal)
                                     │
                                     ▼
                 [ DISTRIBUTED MULTI-ASSET WORKER CORE ]
               (Async WebSocket Ingestion: BTC | ETH | SOL)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
[ MASTER ORCHESTRATOR ]     [ DENIAL ANALYTICS ]       [ PERFORMANCE HUB ]
(Central 2% Risk Clamp)    (Negative Space Mining)    (Real-Time Telemetry)
==========================================================================
## ⚡ Core Engine Features

* **Distributed Ingestion Core (`live_paper_engine.py`)**
  * Manages asynchronous multi-asset network workers isolated within dedicated, headless `tmux` execution canvases.
  * Processes concurrent streaming WebSocket data feeds for BTC, ETH, and SOL with zero database read/write thread contention.

* **Autonomous Self-Healing Watchdog (`supervisor_daemon.py`)**
  * Tracks core system vitality registers continuously by auditing shared disk updates at a sub-second pulse delta ($<0.1$s).
  * Triggers automated OS-level command injections to cleanly drop and reboot background workers if data feeds freeze for more than 45 seconds.
  * Implements a strict, hard-capped recovery limit circuit breaker to completely eliminate cascading infinite restart loops.

* **Centralized Portfolio Governance (`master_orchestrator.py`)**
  * Intercepts transaction requests globally from independent asset workers to validate macro account exposure states.
  * Extinguishes correlated sector vulnerability by enforcing a strict, hard-capped **2% maximum total portfolio heat limit**.

* **True Negative Intelligence Mining (`denial_analyzer.py`)**
  * Maps out the framework's "negative space" by indexing exactly *why* evaluation gates block specific trade setups.
  * Itemizes structural displacement failures, low-conviction scores, and orchestration boundaries directly to an independent SQLite ledger for empirical filter optimization.

* **Deterministic Candle Aggregator Matrix (`core/candle_aggregator.py`)**
  * Implements a high-performance mathematical downsampling pipeline to convert 1-minute streaming blocks into pristine macro bodies (5m, 15m, 1h) on the fly.
  * Calculates mathematically exact OHLC boundaries, ensuring longer-term strategy cartridges remain completely insulated from microstructure market noise.

* **Profile Cartridge Architecture (`strategies/`)**
  * Completely decouples raw technical data execution pipelines from strategy risk boundaries and confirmation rulesets.
  * Allows timeframes, target risk-reward scales, and validation criteria to slide into the engine on the fly via modular profiles (`INTRADAY_SNIPER`, `SWING_VANGUARD`).

* **High-Fidelity Batch Simulation Harness (`batch_replay_harness.py`)**
  * An isolated simulation chamber designed to replay thousands of historical intervals through production analytical engines at accelerated warp speeds.
  * Maintains a strict database air-gap to keep forward paper-trading logs completely pristine and free of research contamination.

---

## 📁 Repository Blueprint

```text
apex-quant-systems/
│
├── core/
│   ├── candle_aggregator.py       # High-performance mathematical OHLC downsampler
│   └── regime_classifier.py       # Algorithmic macro environment classifier
│
├── strategies/
│   ├── base_profile.py            # Structural parameter abstract blueprint
│   └── profile_manifest.py        # Hot-swappable profile cartridges (Intraday vs Swing)
│
├── structure_engine/
│   ├── swing_detector.py          # Real-time high/low swing structural pivot engine
│   └── displacement_detector.py   # Absolute momentum validation matrix
│
├── live_paper_engine.py           # Multi-asset real-time background execution runner
├── supervisor_daemon.py           # Fault-tolerant process monitor and auto-recovery loop
├── batch_replay_harness.py        # Multi-profile macro backtesting & time-warp suite
├── historical_downloader.py       # Paginated local data caching engine (prevents API limits)
├── master_orchestrator.py         # Portfolio risk governor & correlation shield
├── denial_analyzer.py             # Rejection audit matrix & filter efficiency calculator
└── analytics_dashboard.py         # Forward edge health & telemetry tracking suite

---

---

---

## 🛡️ Guardrails and Operational Rules

* **1. Environment Separation (Air-Gap)**
  * Live forward-tracking data arrays are strictly isolated from backtest logs via distinct database tables to eliminate research and evaluation data contamination.

* **2. Asymmetry Preservation**
  * System parameters target a mandatory, uncompromised $1:4$ risk-to-reward ratio floor. This insulates equity curves from drawdowns via structural mathematical asymmetry, requiring a very low break-even threshold:

$$WR_{\text{breakeven}} = \frac{1}{1 + \text{RR}} = 20\%$$

* **3. Core Logic Freeze**
  * Strategy parameters and structural mathematical filters remain 100% locked down during active tracking runs to protect the scientific integrity of empirical logs and completely prevent curve-fitting overfitting.

---

## 🚀 Getting Started

### 1. Initialize and Start Ingestion Core
Spin up your asynchronous multi-asset network workers inside an isolated background shell canvas:
```bash
tmux new-session -d -s apex_scout 'python3 live_paper_engine.py'
```

### 2. Arm Autonomous Supervisor Protection
Launch the self-healing monitor in your active workspace to safeguard the live websocket streams:
```bash
python3 supervisor_daemon.py
```

### 3. Run Batch Multi-Profile Replay Simulations
Execute historical time-warp experiments over deep local cached datasets without interrupting production lines:
```bash
python3 batch_replay_harness.py
```

### 4. Audit Negative Space Intelligence
Extract your exact filter efficiency breakdown to review why evaluation gates blocked specific transaction signals:
```bash
python3 denial_analyzer.py
```

---
*Developed as an adaptive, enterprise-grade research platform for systematic portfolio automation.*
