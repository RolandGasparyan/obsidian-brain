# Trading Strategies Testing Engine

This document is the entry point for the **Trading Strategies Testing Engine** — the multi-agent practicing arena where all AI agents test, refine, and upgrade their trading strategies 24/7 using real market data in paper trading mode.

## What Is the Testing Engine?

The Testing Engine is an autonomous, competitive arena where multiple AI agents (including the master **Trading Guru**) practice trading strategies against each other in real-time. Agents are self-learning and self-upgrading, continuously improving their performance without human intervention. The engine operates exclusively in paper trading mode using live market data, ensuring zero capital risk during the learning phase.

## Quick Links

| Document | Purpose |
| :--- | :--- |
| [`docs/testing-engine/README.md`](docs/testing-engine/README.md) | Full documentation package index |
| [`docs/testing-engine/TECH_SPEC.md`](docs/testing-engine/TECH_SPEC.md) | Technical specification and system architecture |
| [`docs/testing-engine/IMPLEMENTATION_GUIDE.md`](docs/testing-engine/IMPLEMENTATION_GUIDE.md) | Step-by-step implementation with verification checkpoints |
| [`docs/testing-engine/TESTING_PROTOCOL.md`](docs/testing-engine/TESTING_PROTOCOL.md) | Rigorous testing and validation procedures |
| [`docs/testing-engine/VERIFICATION_CHECKLIST.md`](docs/testing-engine/VERIFICATION_CHECKLIST.md) | Master checklist with 69 items and sign-off section |
| [`skills/system-verification-docs/SKILL.md`](skills/system-verification-docs/SKILL.md) | Reusable skill for generating verification documentation |

## Core Specifications at a Glance

| Parameter | Value |
| :--- | :--- |
| **Allowed Assets** | XRP, AVAX, SOL, BTC, ETH |
| **Trading Mode** | Spot Mode only |
| **Trade Direction** | Short trades only (Long trades strictly prohibited) |
| **Operation Hours** | 24/7 continuous |
| **Stop Condition** | Daily loss threshold reached |
| **Position Sizing** | `POSITION = RISK ÷ STOP%` × 0.25 Kelly Adjustment |
| **Profit Securing** | $100 threshold → cold wallet transfer |
| **Agent Intelligence** | Gods Level + DeepSeek-Math + Claude integration |

## Architecture Overview

The engine consists of five core components working in unison:

1. **Multi-Agent Practicing Arena** — Hosts all competing AI agents including the Trading Guru master agent.
2. **Real-Time Market Data Ingestion Layer** — Streams live price ticks, order book, and volume data from exchange APIs.
3. **Paper Trading Execution Engine** — Simulates Spot Mode trading with realistic slippage and latency.
4. **Performance Analytics & Leaderboard** — Tracks and ranks all agents by win rate and profit generated.
5. **Self-Learning Knowledge Base** — The Trading Guru observes peer performance and upgrades its own logic continuously.

## Getting Started

To implement and verify the engine, follow the phases in the [Implementation Guide](docs/testing-engine/IMPLEMENTATION_GUIDE.md):

1. **Phase 1** — Infrastructure setup and environment verification
2. **Phase 2** — Market data and execution layer integration
3. **Phase 3** — AI agent deployment and configuration
4. **Phase 4** — Trading logic and risk management enforcement
5. **Phase 5** — Access control and final 72-hour validation test

Once all 69 items in the [Verification Checklist](docs/testing-engine/VERIFICATION_CHECKLIST.md) are signed off, the engine is approved for continuous operation.
