# Trading Guru - ULTIMATE Gods Level Trading System + OMNI-GOD

## Overview

Trading Guru is a multi-agent AI cryptocurrency trading analysis platform designed for "ULTIMATE Gods Level" and "OMNI-GOD" architectures. It features 8 specialized AI GODS that compete for maximum profit through an intelligent consensus voting system. The platform offers real-time market analysis, tier-based progression, and incorporates self-preservation protocols. It operates exclusively in **SHORTS ONLY** mode on Gate.io Futures with a 24/7 auto-trading loop, emphasizing aggressive profit maximization and robust risk management. The project aims to provide an institutional-grade automated trading solution with advanced risk management and continuous profit generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend
- **Framework**: React 18 with TypeScript, Wouter for routing.
- **State Management**: TanStack Query (server state), React useState (local state).
- **Styling**: Tailwind CSS with shadcn/ui (New York style), supporting dark/light modes.
- **Build Tool**: Vite.

### Backend
- **Runtime**: Node.js with Express.
- **Language**: TypeScript with ES modules.
- **API Pattern**: RESTful endpoints with Server-Sent Events (SSE) for streaming.
- **Build**: esbuild.

### Data Flow
Market data and agent analyses are streamed via SSE. A sequential analysis by six agents is followed by consensus calculation, with results stored in an analysis history.

### Agent System
A three-phase architecture coordinates six AI agents:
- **Sentinels**: Grok (news/sentiment) and Llama (scalping).
- **Strategists**: GPT-5 (macro analysis) and Claude (psychology/behavior).
- **Executioners**: DeepSeek (quant/math) and Qwen (patterns/harmonics).

### Key Design Patterns & Features
- **Streaming SSE**: Real-time analysis updates.
- **Consensus Calculation**: Aggregates agent signals with confidence weighting.
- **Live Market Data**: Real-time data from Gate.io, with simulated data fallback.
- **Gods Mode: Profitable Levels Edition**: Combines agent entry zones for "Kill Zone Synthesis" with a "Verdict System" (EXECUTE, WAIT, NO_TRADE).
- **Trinity of Profit System**: Scores trading pairs and applies dynamic strategies (WATERFALL, SCALPING, SNOWBALL, DOUBLING, TURBO) based on market conditions.
- **Dynamic Strategy Gods Level (TRIPLED MODE)**: Adapts strategies (PYRAMID, WATERFALL, SCALPING, DOUBLING) based on ADX and performance.
- **LEVEL 13 GOD MODE**: A 24/7 auto-loop system with boosted position power and multi-AI model engagement.
- **Wolf Pack Trading System**: Multi-pair parallel trading with "Unbreakable Protection Suite".
- **Engine Validation System**: Governors, circuit breakers, and "Smart Gates" for trade approval.
- **24/7 Auto-Analysis Loop**: Continuous analysis with symbol rotation and "Auto-Pilot Trading Modes".
- **ULTIMATE GODS LEVEL STRATEGY**: Features 5 trading modes, 15 secret strategies, market regime detection, multi-factor edge calculation, 6 balance tiers, whale detection, sentiment analysis, and ATR-based risk management.
- **GODS LEVEL AI Competition System**: 8 AI GODS compete, with capital rebalancing and adaptive strategy allocation.
- **OMNI-GOD System**: Institutional-grade with 5 modules: SMC Sniper, Risk Guardian, Capital Manager, Phoenix Protocol, and Genetic Optimizer.
- **Smart-Dynamic Trading System**: Confidence-based trading modes (AGGRESSIVE, NORMAL, SAFE, NO_TRADE), dynamic balance tiers, and a self-preservation protocol.
- **Auto-Withdraw System**: Automatically withdraws profits to a cold wallet after every $100 profit.
- **ScalpTrap Engine**: Breakeven protection system moving stop-loss to entry at TP1. Incorporates dynamic leverage based on confidence and thesis invalidation logic.
- **ScalperBot System**: Advanced scalping for quick trades with RSI-based entries, partial exits, and confidence-based leverage.
- **Multi-Coin God Engine**: Trades 5 coins independently with 8 AI models, each having specific strategies and risk management. Features an AI competition system for capital allocation and hybrid withdrawal.
- **Persistent Trading Configuration**: All trading settings, balance protection, and withdrawal configurations are stored permanently in PostgreSQL.
- **Smart Loss Prediction Engine**: Intelligent loss prevention using 12 market indicators to predict risk and block trades under critical conditions.
- **24/7 Uncrashable Background Worker**: Autonomous trading worker with comprehensive health monitoring, watchdog system, and auto-recovery features for continuous operation.

### Technical Indicators
- Ichimoku Cloud (Span A, Span B, Tenkan, Kijun)
- RSI (14 period)
- MACD (12, 26, 9)
- Bollinger Bands (20 period, 2 std dev)
- ATR (14 period)
- MFI (Money Flow Index)

### Database Schema
- **Users**: For authentication.
- **Conversations/Messages**: Stores AI interactions.
- **Analysis History**: Records consensus results, signals, and confluence scores.
- **Wolf Pack Trades**: Logs executed trades including PnL, strategy, and market conditions.
- **Trading Config**: Stores persistent trading settings, balance protection, and withdrawal configurations.

### Production Engine Package
A Python-based production trading engine for VPS deployment, featuring auto-restart, config persistence, health monitoring, auto-withdraw, 8 AI traders, and high uptime.

## External Dependencies

### AI/LLM Services
- **OpenAI API**: Used for all agent analysis via Replit AI Integrations.

### Database
- **PostgreSQL**: Primary database, using drizzle-orm with drizzle-zod.

### Replit Integrations
- **Audio**: Voice recording, playback, speech-to-text.
- **Chat**: Conversation storage, streaming responses.
- **Image**: Image generation (gpt-image-1).
- **Batch Processing**: Rate-limited with retries.

### UI Components
- **Radix UI**: Headless component primitives.
- **shadcn/ui**: Pre-styled component library.
- **Lucide React**: Icon library.

### Trading Platform
- **Gate.io Futures API**: For real-time market data and direct trade execution.