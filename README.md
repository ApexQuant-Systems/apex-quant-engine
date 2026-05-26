# Apex Quant Systems: Distributed Research & Execution Framework (v1.0)

A highly decoupled, fault-tolerant, and modular multi-asset quantitative trading infrastructure engine engineered for real-time WebSocket ingestion, multi-timeframe candle synthesis, centralized risk governance, and isolated high-fidelity simulation testing.

---

## 🛠️ System Architecture

The platform is designed around a unified hardware chassis model where the underlying core infrastructure remains completely stable, while strategic alpha logic and timeframe configurations slip into the pipeline via hot-swappable parameter cartridges.

```text
               ┌──────────────────────────────────────────────┐
               │         AUTONOMOUS SUPERVISOR DAEMON         │
               │   (Monitors Vitality Registers / Auto-Heals) │
               └──────────────────────┬───────────────────────┘
                                      │ (Pulse Verified Every 10s)
                                      ▼
               ┌──────────────────────────────────────────────┐
               │       DISTRIBUTED MULTI-ASSET CORE           │
               │  (Asynchronous BTC, ETH, SOL Workers inside  │
               │   isolated background tmux matrix session)   │
               └──────────────────────┬───────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  MASTER ORCHESTRATOR  │ │   DENIAL ANALYTICS    │ │ PERFORMANCE DASHBOARD │
│ (Enforces Centralized │ │ (Indexes Negative-    │ │  (Provides Real-Time  │
│  2% Portfolio Caps)   │ │  Space Alpha Intel)   │ │  Edge Telemetry Read) │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘

⚡ Core Engine Features
Distributed Multi-Asset Core (live_paper_engine.py): Asynchronous network workers running inside isolated, headless tmux cells processing live, concurrent WebSocket data streams for BTC, ETH, and SOL simultaneously with zero thread contention.
Autonomous Self-Healing Supervisor (supervisor_daemon.py): A lightweight background watchdog layer tracking system vitality via shared disk registers. Operates at a sub-second pulse delta ($<0.1$s) and is armed with automated OS-level command injection routines to recover frozen websocket connections completely unattended. Built-in retry caps protect against infinite restart loops.
Centralized Portfolio Governance (master_orchestrator.py): A global portfolio governor that abstracts risk clearance from individual strategy workers. Enforces a strict, hard-capped 2% total portfolio heat limit to insulate the capital sheet from toxic multi-asset sector correlations.
True Negative Intelligence Lab (denial_analyzer.py): A dedicated analytics engine designed to index the system's "negative space." By recording exactly why evaluation gates block a transaction (Displacement Failure, Low Conviction Score, Orchestrator Boundary), it provides data-driven filter efficiency metrics.
Deterministic Candle Aggregator Matrix (core/candle_aggregator.py): High-performance mathematical downsampling pipeline that compresses 1-minute streaming blocks into structurally pristine higher timeframe macro bars (5m, 15m, 1h) on the fly, keeping higher-timeframe strategies insulated from microstructure market noise.
Profile Cartridge Architecture (strategies/): Universal hardware-chassis architecture where strategy personalities are completely decoupled from core pipeline logic. Strategy parameters, targets, and timeframes slide into the engine on the fly via swappable software cartridges (INTRADAY_SNIPER, SWING_VANGUARD).
High-Fidelity Batch Simulation Harness (batch_replay_harness.py): An isolated sandbox testing utility that replays thousands of historical intervals through production analytical layers. Fully air-gapped from live tracking journals via distinct localized ledger spaces to prevent data contamination.

