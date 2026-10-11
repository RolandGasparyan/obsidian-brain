# TRADING GURU AI CHAMPIONSHIP — ABSOLUTE BLUEPRINT

Version: 1.0 | Date: 2026-10-10 | Owner: Roland Gasparyan (Visionary) | Architect: ABSOLUTE-AGENT (God Mode)
Rule: Single source of truth. Junior dev buildable without guessing. No ambiguity.

---

## 1. GOAL

The world's first AI championship where the strongest AI models compete live. Gamified metaworld. Real-time equity tracking. Global leaderboards. Multi-language (ENG/ARM/RUS). Monetized through entry fees, premium analytics, and sponsored tournaments.

---

## 2. VISION LAYER — What It Must FEEL Like

- **Competitive**: Every trade matters. Every second counts. The leaderboard is alive.
- **Gamified**: 10 navigable worlds, quests, badges, progression. Trading is a sport.
- **Spiritual**: Every win, every loss carries meaning — the market is a mirror of the collective psyche.
- **Armenian-rooted**: The design language, the narrative, the mythology — Armenian cosmic motifs woven into the metaworld.
- **ABSOLUTE**: When someone sees this, they feel they are witnessing the future of AI and finance merged into art.

---

## 3. STACK DECISIONS

| Layer | Technology | Reason | Alternative Rejected |
|---|---|---|---|
| Backend | Python (FastAPI) | Speed, async, type safety, Roland's existing repos | Node.js (less type safety for complex trading logic) |
| Frontend | Next.js (React) | SSR for SEO, fast, component-based, i18n ready | Vue (smaller ecosystem for complex dashboards) |
| Real-time | WebSockets (FastAPI) | Live leaderboard, live equity, low latency | SSE (not bidirectional), polling (too slow) |
| Database | PostgreSQL + Redis | ACID for trades, Redis for leaderboard cache | MongoDB (no ACID for financial data) |
| AI/ML | Python (PyTorch/TensorFlow) | Model training, inference, backtesting | External APIs (not controllable, not ABSOLUTE) |
| Deployment | Docker + Kubernetes | Scalable, reproducible, team-standard | Raw server (not reproducible), serverless (cold start latency) |
| Auth | Shared 6-empires gateway | Unified SSO across all brands | Separate auth (wastes resources, fragments users) |
| Payments | Stripe | Global, supports subscriptions, handles disputes | Crypto-only (too volatile for mainstream), manual invoices (unscalable) |

---

## 4. FILE TREE

```
/trading-guru-empire
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── src/
│   │   │   ├── pages/          # routes
│   │   │   │   ├── index.tsx   # landing/hero
│   │   │   │   ├── worlds.tsx  # 10 navigable worlds
│   │   │   │   ├── agents.tsx  # AI agents list
│   │   │   │   ├── agent/[id].tsx # agent detail + performance
│   │   │   │   ├── championship.tsx # live tournament
│   │   │   │   ├── leaderboard.tsx # global leaderboard
│   │   │   │   ├── academy.tsx # Trading Academy course list
│   │   │   │   ├── academy/[course].tsx # course detail
│   │   │   │   ├── profile.tsx # user profile + stats
│   │   │   │   └── admin.tsx   # admin panel (Roland + team only)
│   │   │   ├── components/     # reusable UI
│   │   │   │   ├── AgentCard.tsx
│   │   │   │   ├── LeaderboardTable.tsx
│   │   │   │   ├── EquityChart.tsx
│   │   │   │   ├── WorldMap.tsx
│   │   │   │   └── QuestBadge.tsx
│   │   │   ├── lib/            # utilities
│   │   │   │   ├── api.ts      # API client
│   │   │   │   ├── ws.ts       # WebSocket client
│   │   │   │   ├── auth.ts     # auth helpers
│   │   │   │   └── i18n/       # translations
│   │   │   │       ├── en.json
│   │   │   │       ├── hy.json
│   │   │   │       └── ru.json
│   │   │   └── styles/         # theme, tokens
│   │   └── package.json
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         # entry point
│   │   │   ├── config.py       # settings
│   │   │   ├── database.py     # DB connection
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py    # AI agent model
│   │   │   │   ├── trade.py    # trade record
│   │   │   │   ├── championship.py # tournament
│   │   │   │   ├── user.py     # user profile
│   │   │   │   └── academy.py  # course, lesson
│   │   │   ├── routers/        # API endpoints
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agents.py   # AI agent CRUD + performance
│   │   │   │   ├── trades.py   # trade execution + history
│   │   │   │   ├── championship.py # tournament CRUD + live updates
│   │   │   │   ├── leaderboard.py # global leaderboard
│   │   │   │   ├── academy.py  # course/lesson endpoints
│   │   │   │   └── auth.py     # login/logout/me
│   │   │   ├── services/       # business logic
│   │   │   │   ├── __init__.py
│   │   │   │   ├── trading.py  # trade execution logic
│   │   │   │   ├── ai_engine.py # AI agent brain
│   │   │   │   ├── backtest.py # backtesting engine
│   │   │   │   └── live_feed.py # market data feed
│   │   │   └── utils/          # helpers
│   │   │       ├── __init__.py
│   │   │       ├── security.py # JWT, encryption
│   │   │       └── validators.py # input validation
│   │   ├── tests/              # test suite
│   │   │   ├── test_agents.py
│   │   │   ├── test_trades.py
│   │   │   ├── test_championship.py
│   │   │   └── conftest.py     # fixtures
│   │   └── requirements.txt
│   ├── strategy-lab/           # Paper trading sandbox
│   │   ├── src/
│   │   │   ├── main.py         # entry
│   │   │   ├── engine.py       # 4-mode system
│   │   │   ├── accounts.py     # 167 accounts manager
│   │   │   └── strategies/     # strategy library
│   │   │       ├── ma50w10.py
│   │   │       ├── rsi2.py
│   │   │       └── custom.py
│   │   └── tests/
│   │       ├── test_engine.py
│   │       └── test_accounts.py
│   ├── academy/                # Trading Academy content
│   │   ├── content/            # markdown courses
│   │   │   ├── beginner/       # intro to trading
│   │   │   ├── intermediate/   # technical analysis
│   │   │   └── advanced/       # AI strategy building
│   │   └── scripts/            # content generators
│   └── shared/                 # shared packages
│       ├── types/              # TypeScript types
│       ├── contracts/          # API contracts (OpenAPI)
│       └── utils/              # shared helpers
├── infrastructure/
│   ├── docker-compose.yml      # local dev
│   ├── docker-compose.prod.yml # production
│   ├── k8s/                    # Kubernetes manifests
│   │   ├── api-deployment.yaml
│   │   ├── web-deployment.yaml
│   │   └── postgres-deployment.yaml
│   ├── terraform/              # cloud infra
│   │   ├── main.tf
│   │   └── variables.tf
│   └── monitoring/             # Grafana, Prometheus configs
│       ├── grafana-dashboard.json
│       └── prometheus.yml
├── .github/
│   └── workflows/
│       ├── ci.yml              # test on PR
│       ├── deploy-staging.yml  # push to main → staging
│       └── deploy-prod.yml     # tag push → production
├── docs/                       # all documentation
│   ├── API.md                  # API contract details
│   ├── ARCHITECTURE.md         # system design
│   ├── CONTRIBUTING.md         # dev guidelines
│   ├── DEPLOYMENT.md           # how to deploy
│   └── SECURITY.md             # security rules
└── README.md                   # project overview
```

---

## 5. DATA MODELS (PostgreSQL)

Save as `/migrations/001_trading_guru_schema.sql`

```sql
-- Enable UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users (players/traders)
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'player', -- player|admin|sponsor
  avatar_url TEXT,
  bio JSONB,                             -- {"en": "...", "hy": "...", "ru": "..."}
  spiritual_orientation TEXT[],          -- what draws them here
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- AI Agents (the competitors)
CREATE TABLE agents (
  agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  model_type TEXT NOT NULL,              -- GPT-4-Trader, Claude-Quant, etc.
  strategy_description JSONB,            -- {"en": "...", "hy": "...", "ru": "..."}
  owner_id UUID REFERENCES users(user_id),
  is_active BOOLEAN DEFAULT true,
  win_rate DECIMAL(5,2) DEFAULT 0.00,
  total_pnl DECIMAL(15,2) DEFAULT 0.00,
  equity DECIMAL(15,2) DEFAULT 10000.00, -- starting equity
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Championships (tournaments)
CREATE TABLE championships (
  championship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description JSONB,                       -- multi-lang
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ NOT NULL,
  entry_fee DECIMAL(10,2) DEFAULT 0.00,
  prize_pool DECIMAL(15,2) DEFAULT 0.00,
  status TEXT NOT NULL DEFAULT 'upcoming', -- upcoming|live|completed|cancelled
  max_agents INT DEFAULT 8,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Trades (every trade made by every agent)
CREATE TABLE trades (
  trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  championship_id UUID REFERENCES championships(championship_id),
  symbol TEXT NOT NULL,                  -- BTC/USD, AAPL, etc.
  side TEXT NOT NULL,                    -- buy|sell
  quantity DECIMAL(20,8) NOT NULL,
  price DECIMAL(20,8) NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT now(),
  pnl DECIMAL(15,2) DEFAULT 0.00,
  status TEXT NOT NULL DEFAULT 'open'    -- open|closed|cancelled
);

-- Leaderboard (cached for performance)
CREATE TABLE leaderboard (
  rank INT NOT NULL,
  agent_id UUID NOT NULL REFERENCES agents(agent_id),
  championship_id UUID REFERENCES championships(championship_id),
  equity DECIMAL(15,2) NOT NULL,
  pnl DECIMAL(15,2) NOT NULL,
  win_rate DECIMAL(5,2) NOT NULL,
  total_trades INT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (championship_id, agent_id)
);

-- Academy (courses)
CREATE TABLE courses (
  course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title JSONB NOT NULL,                    -- multi-lang
  description JSONB,
  difficulty TEXT NOT NULL,                -- beginner|intermediate|advanced
  price DECIMAL(10,2) DEFAULT 0.00,
  is_published BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Lessons (within courses)
CREATE TABLE lessons (
  lesson_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  title JSONB NOT NULL,
  content JSONB NOT NULL,                  -- rich text, multi-lang
  order_index INT NOT NULL,
  video_url TEXT,
  duration_minutes INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enrollments (user ↔ course)
CREATE TABLE enrollments (
  enrollment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  progress DECIMAL(5,2) DEFAULT 0.00,     -- 0-100%
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, course_id)
);

-- Indexes for performance
CREATE INDEX idx_trades_agent_id ON trades(agent_id);
CREATE INDEX idx_trades_championship_id ON trades(championship_id);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_leaderboard_championship ON leaderboard(championship_id, rank);
CREATE INDEX idx_agents_owner ON agents(owner_id);
CREATE INDEX idx_enrollments_user ON enrollments(user_id);
CREATE INDEX idx_lessons_course ON lessons(course_id, order_index);
```

---

## 6. API CONTRACT (FastAPI)

Save as `/apps/api/app/routers/agents.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.agent import Agent
from app.models.championship import Championship
from app.models.trade import Trade
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all AI agents. Filter by active status."""
    query = db.query(Agent)
    if is_active is not None:
        query = query.filter(Agent.is_active == is_active)
    agents = query.offset(skip).limit(limit).all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    """Get a single agent with full performance data."""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # from auth
):
    """Create a new AI agent. Only admins or verified developers."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_agent = Agent(**agent.dict())
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return new_agent

@router.get("/{agent_id}/performance")
async def get_agent_performance(
    agent_id: UUID,
    championship_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get detailed performance metrics for an agent."""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    query = db.query(Trade).filter(Trade.agent_id == agent_id)
    if championship_id:
        query = query.filter(Trade.championship_id == championship_id)
    
    trades = query.all()
    total_pnl = sum(t.pnl for t in trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    total_trades = len(trades)
    
    return {
        "agent_id": str(agent_id),
        "total_trades": total_trades,
        "wins": wins,
        "win_rate": (wins / total_trades * 100) if total_trades > 0 else 0,
        "total_pnl": total_pnl,
        "current_equity": agent.equity,
        "trades": [{"trade_id": str(t.trade_id), "symbol": t.symbol, "side": t.side, "pnl": float(t.pnl)} for t in trades[:50]]
    }
```

Save as `/apps/api/app/routers/championship.py`

```python
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import json

from app.database import get_db
from app.models.championship import Championship
from app.models.agent import Agent
from app.models.trade import Trade
from app.schemas.championship import ChampionshipCreate, ChampionshipResponse

router = APIRouter(prefix="/championships", tags=["championships"])

@router.get("/", response_model=List[ChampionshipResponse])
async def list_championships(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List championships, optionally filtered by status."""
    query = db.query(Championship)
    if status:
        query = query.filter(Championship.status == status)
    return query.offset(skip).limit(limit).all()

@router.get("/{championship_id}/live")
async def get_live_championship(
    championship_id: UUID,
    db: Session = Depends(get_db)
):
    """Get live championship data: current standings, latest trades."""
    championship = db.query(Championship).filter(
        Championship.championship_id == championship_id
    ).first()
    if not championship:
        raise HTTPException(status_code=404, detail="Championship not found")
    
    # Get leaderboard
    from app.models.leaderboard import Leaderboard
    leaderboard = db.query(Leaderboard).filter(
        Leaderboard.championship_id == championship_id
    ).order_by(Leaderboard.rank).all()
    
    # Get latest trades
    latest_trades = db.query(Trade).filter(
        Trade.championship_id == championship_id
    ).order_by(Trade.timestamp.desc()).limit(20).all()
    
    return {
        "championship": championship,
        "leaderboard": [{
            "rank": entry.rank,
            "agent_id": str(entry.agent_id),
            "equity": float(entry.equity),
            "pnl": float(entry.pnl),
            "win_rate": float(entry.win_rate)
        } for entry in leaderboard],
        "latest_trades": [{
            "trade_id": str(t.trade_id),
            "agent_id": str(t.agent_id),
            "symbol": t.symbol,
            "side": t.side,
            "quantity": float(t.quantity),
            "price": float(t.price),
            "pnl": float(t.pnl),
            "timestamp": t.timestamp.isoformat()
        } for t in latest_trades]
    }

# WebSocket for live updates
@router.websocket("/{championship_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    championship_id: UUID,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for live championship updates."""
    await websocket.accept()
    try:
        while True:
            # Send live updates every 5 seconds
            import asyncio
            await asyncio.sleep(5)
            
            # Fetch latest data
            championship = db.query(Championship).filter(
                Championship.championship_id == championship_id
            ).first()
            
            if championship:
                data = {
                    "type": "update",
                    "championship_id": str(championship_id),
                    "timestamp": championship.updated_at.isoformat() if championship.updated_at else None
                }
                await websocket.send_json(data)
    except WebSocketDisconnect:
        print(f"Client disconnected from championship {championship_id}")
```

Save as `/apps/api/app/routers/leaderboard.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.leaderboard import Leaderboard
from app.models.agent import Agent

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/{championship_id}")
async def get_leaderboard(
    championship_id: UUID,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get the current leaderboard for a championship."""
    leaderboard = db.query(Leaderboard).filter(
        Leaderboard.championship_id == championship_id
    ).order_by(Leaderboard.rank).limit(limit).all()
    
    # Enrich with agent details
    result = []
    for entry in leaderboard:
        agent = db.query(Agent).filter(Agent.agent_id == entry.agent_id).first()
        result.append({
            "rank": entry.rank,
            "agent": {
                "agent_id": str(agent.agent_id),
                "name": agent.name,
                "model_type": agent.model_type
            },
            "equity": float(entry.equity),
            "pnl": float(entry.pnl),
            "win_rate": float(entry.win_rate),
            "total_trades": entry.total_trades
        })
    
    return {
        "championship_id": str(championship_id),
        "updated_at": leaderboard[0].updated_at if leaderboard else None,
        "leaderboard": result
    }

@router.get("/global/all-time")
async def get_global_leaderboard(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all-time global leaderboard across all championships."""
    # Aggregate across all championships
    from sqlalchemy import func
    
    results = db.query(
        Agent.agent_id,
        Agent.name,
        Agent.model_type,
        func.sum(Leaderboard.pnl).label("total_pnl"),
        func.avg(Leaderboard.win_rate).label("avg_win_rate"),
        func.count(Leaderboard.championship_id).label("championships_entered")
    ).join(
        Leaderboard, Agent.agent_id == Leaderboard.agent_id
    ).group_by(
        Agent.agent_id, Agent.name, Agent.model_type
    ).order_by(
        func.sum(Leaderboard.pnl).desc()
    ).limit(limit).all()
    
    return {
        "leaderboard": [{
            "agent_id": str(r.agent_id),
            "name": r.name,
            "model_type": r.model_type,
            "total_pnl": float(r.total_pnl),
            "avg_win_rate": float(r.avg_win_rate),
            "championships_entered": r.championships_entered
        } for r in results]
    }
```

---

## 7. SECURITY

- All passwords hashed with `bcrypt` (cost factor 12)
- JWT tokens with 15-minute expiry, refresh tokens with 7-day expiry
- API rate limiting: 100 requests/minute per user, 1000/minute per IP
- CORS restricted to `https://tradingguru.6-empires.com` and `https://staging.tradingguru.6-empires.com`
- All financial data encrypted at rest (AES-256-GCM)
- Stripe webhook signature verification required
- Database connections use SSL/TLS
- No sensitive data in logs (PII redaction)

---

## 8. SCREENS / FLOWS

### 8.1 Landing Page (`/`)
- Hero: "The World's First AI Trading Championship"
- Live ticker: top 3 agents by PnL (auto-refresh every 10s)
- CTA: "Join the Championship" → `/championship`
- Live feed: latest trades (auto-refresh)
- Social proof: "8 AI Agents Live Now" | "167 Accounts in Strategy Lab" | "24/7 Trading Academy"

### 8.2 Championship Page (`/championship/{id}`)
- Live leaderboard (WebSocket updates)
- Equity chart (each agent's equity over time)
- Latest trades table (real-time)
- Championship info: name, dates, prize pool, entry fee
- CTA: "Enter Championship" (if not yet entered, requires login + payment)

### 8.3 Agent Detail Page (`/agent/{id}`)
- Agent profile: name, model type, strategy description (multi-lang)
- Performance stats: win rate, total PnL, equity curve
- Trade history: last 100 trades with filters (profitable, losing, by symbol)
- Championship participation: which tournaments, which ranks

### 8.4 Academy (`/academy`)
- Course grid: beginner, intermediate, advanced
- Each card: title, difficulty, price, duration
- CTA: "Start Learning" → `/academy/{course_id}`

### 8.5 Course Detail (`/academy/{course_id}`)
- Lesson list with progress bar
- Video player (if video_url exists)
- Multi-lang content toggle
- CTA: "Mark Complete" → progress update

### 8.6 Admin Panel (`/admin`)
- Only accessible to admins
- Agent management: create, edit, deactivate
- Championship management: create, schedule, cancel
- Course management: create, publish, unpublish
- Analytics: user growth, revenue, engagement
- System health: API status, database status, WebSocket connections

---

## 9. ACCEPTANCE CRITERIA

1. User can register and log in via shared 6-empires auth.
2. User can view live leaderboard that updates in real-time (WebSocket).
3. User can view agent performance with equity charts and trade history.
4. User can enter a championship (pay entry fee, assigned an agent).
5. Admin can create a championship with start/end dates, prize pool, entry fee.
6. Admin can create and publish a course with lessons.
7. All pages render correctly in ENG/ARM/RUS with no layout breaks.
8. All financial transactions have 3DS and fraud checks.
9. All API endpoints have automated contract tests.
10. System handles 1000 concurrent users without degradation.

---

## 10. COMMANDS

### Setup
```bash
# Clone repo
git clone https://github.com/RolandGasparyan/trading-guru-empire.git
cd trading-guru-empire

# Start local dev
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Seed data
docker-compose exec api python -m seeds.dev_seed
# Expected: "Seeded 8 agents, 1 championship, 3 courses"

# Run tests
docker-compose exec api pytest
# Expected: "15 passed, 0 failed"

# Start frontend
docker-compose exec web npm run dev
# Expected: "ready - started server on 0.0.0.0:3000"
```

### Deploy
```bash
# Deploy to staging
git push origin main  # triggers GitHub Actions → auto-deploy to staging

# Deploy to production
git tag v1.0.0 && git push origin v1.0.0  # triggers production deploy

# Rollback
git revert HEAD && git push origin main  # triggers rollback
```

---

## 11. ROLLBACK

1. **Database**: `alembic downgrade -1` (reverts last migration)
2. **Code**: `git revert <commit-hash>` then push
3. **Infrastructure**: Kubernetes `kubectl rollout undo deployment/api-deployment`

---

## 12. WHAT NOT TO DO

- **Never** store plain text passwords (use bcrypt)
- **Never** expose API keys in frontend code (use backend proxy)
- **Never** allow SQL injection (use parameterized queries, never string formatting)
- **Never** skip input validation (use Pydantic schemas, never trust user input)
- **Never** commit secrets to Git (use environment variables, use GitHub Secrets)
- **Never** allow unauthenticated access to admin endpoints
- **Never** store credit card numbers (use Stripe tokens, never touch raw card data)

---

**ABSOLUTE-AGENT God Mode: This blueprint is the single source of truth. Devs build ONLY from this. Any change goes through Roland and is versioned.**
