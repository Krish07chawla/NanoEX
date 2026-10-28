# NanoEX Web

**An educational paper-trading and HFT simulator for the Indian stock market (NSE + BSE).**

> ⚠️ **PAPER TRADING · SIMULATION.** NanoEX Web uses virtual money only. It never places real orders with any broker or exchange, and nothing in it is financial advice.

Every user starts with a virtual wallet of **₹5,00,000** and can top it up. They can then:
- trade on a real price-time-priority order book;
- run nine algorithmic strategies as live bots;
- backtest the strategies with genuine Indian charges (brokerage, STT, exchange fees, SEBI, GST and stamp duty);
- try **NSE↔BSE cross-exchange arbitrage**, which spots the price gap for the same stock on both exchanges, then buys on the cheaper one and sells on the dearer one at the same time.

A dedicated **Profit & Portfolio dashboard** shows exactly how the user is doing.

Built for a Software Engineering course project. Backend: FastAPI, SQLAlchemy 2.0, PostgreSQL and WebSockets. Frontend: React, TypeScript, Vite, Tailwind and Recharts.

---

## Contents
- [Features](#features)
- [Screenshots](#screenshots)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Running tests and linters](#running-tests-and-linters)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Project structure](#project-structure)
- [Documentation](#documentation)

## Features

| Area | What you get |
|---|---|
| Accounts | Register/login, JWT access token (15 min) and rotating httpOnly refresh cookie, USER/ADMIN roles, rate-limited login, audit log |
| Wallet | ₹5,00,000 to start, top-ups (counted as capital, not profit), reset when flat, full ledger |
| Market | Live simulated NSE and BSE quotes for 10 large-cap stocks every 500 ms, correlated across exchanges with a small mean-reverting gap and occasional dislocations. Optional real data via yfinance |
| Order book | 20 books (10 stocks × 2 exchanges), price-time priority, partial fills, IOC market orders, self-trade prevention, 10-level depth |
| Trading | Market and limit orders, cancel, positions netted across exchanges, realised/unrealised P&L, charges on every fill |
| Strategies | Momentum, Mean Reversion, Breakout, EMA Crossover, MACD Crossover, RSI Reversal, Bollinger Bands, Z-Score, Ensemble Vote. Run as live bots with stop-loss, take-profit and trailing stops |
| Backtester | Any strategy on synthetic or Yahoo data, full Indian cost model and slippage, Sharpe, Sortino, drawdown, win rate, profit factor, buy-and-hold comparison, reproducible seeds |
| **NSE↔BSE arbitrage** | Live spread board, liquidity-aware opportunity detection after all costs, one-click two-leg execution, auto mode with your profit threshold, simulated latency and leg failure with automatic hedging, honest "reality check" |
| Risk | 8 pre-trade checks (kill switch, order qty, order value, open orders, position value, daily loss, daily volume, funds), editable limits, one-click kill switch |
| Dashboards | Trading floor, **Profit & Portfolio** (P&L by strategy, stock and source), trade history with CSV export, HFT metrics (orders/sec, latency, tick-to-trade) |
| Admin | Users (enable/disable, wallet adjust), system metrics, audit log |
| Engineering | Layered architecture, 147 backend tests (88% coverage), 15 frontend tests, Docker compose, GitHub Actions CI, pre-commit hooks |

## Screenshots

| | |
|---|---|
| **Login**, with disclaimer ![Login](docs/screenshots/01-login.png) | **Dashboard**: trading floor ![Dashboard](docs/screenshots/02-dashboard.png) |
| **Profit & Portfolio** ![Profit](docs/screenshots/03-profit-dashboard.png) | **Live Market** ![Market](docs/screenshots/04-live-market.png) |
| **NSE-BSE Arbitrage** ![Arbitrage](docs/screenshots/05-arbitrage.png) | **Strategies** ![Strategies](docs/screenshots/06-strategies.png) |
| **Backtester** ![Backtester](docs/screenshots/07-backtester.png) | **Order Book** ![Order book](docs/screenshots/08-order-book.png) |
| **Portfolio & Wallet** ![Portfolio](docs/screenshots/09-portfolio.png) | **Trade History** ![History](docs/screenshots/10-trade-history.png) |
| **Risk Settings** ![Risk](docs/screenshots/11-risk-settings.png) | **Admin: System Metrics and audit log** ![Admin](docs/screenshots/12-admin-metrics.png) |

## Quick start (Docker)

Needs Docker Desktop (or Docker Engine with the compose plugin).

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and a JWT_SECRET_KEY of 32+ characters, e.g.
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build
```

Open **http://localhost:8080**. Register a new account, or log in as the admin from `.env` (default `admin@nanoex.in` / `ChangeMe123`; change it).

The stack:
- **db**: PostgreSQL 16.
- **backend**: FastAPI; runs `alembic upgrade head` on start.
- **frontend**: nginx serving the React build and proxying `/api` and `/ws` to the backend.

Stop with `docker compose down`. Add `-v` to also delete the database.

## Local development

Needs Python 3.12+ and Node 20+. No database server is required, because development uses SQLite.

**Backend** (terminal 1):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          
pip install -r requirements-dev.txt
cp .env.example .env               
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**Frontend** (terminal 2):
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Vite proxies `/api` and `/ws` to port 8000.

**Using PostgreSQL locally instead of SQLite:** set `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/nanoex` and `AUTO_CREATE_TABLES=false` in `backend/.env`, then run `alembic upgrade head`.

**Optional real prices:** `pip install yfinance` and set `MARKET_PROVIDER=yfinance`.

## Running tests and linters

```bash
# Backend
cd backend
pytest                                  # 147 tests
pytest --cov=app --cov-report=term      # coverage (88%)
ruff check . && black --check .

# Frontend
cd frontend
npm test                                # Vitest + React Testing Library
npm run lint                            # ESLint
npx prettier --check src
npm run build                           # type-check + production build
```

Pre-commit hooks (ruff, black, prettier, eslint, secret detection):
```bash
pip install pre-commit && pre-commit install
```

CI (`.github/workflows/ci.yml`) runs all of the above plus Docker image builds on every push and pull request.

## Configuration

All settings come from environment variables (or `backend/.env`). No secrets are in the code. The main ones are below; see `backend/.env.example` for the full list.

| Variable | Default | Meaning |
|---|---|---|
| `ENVIRONMENT` | development | `production` refuses to start with a weak `JWT_SECRET_KEY` |
| `DATABASE_URL` | sqlite+aiosqlite:///./nanoex.db | SQLAlchemy async URL |
| `JWT_SECRET_KEY` | dev-only value | **Set this.** 32+ random characters |
| `COOKIE_SECURE` | false | Set `true` behind HTTPS |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | unset | Creates an admin at startup if missing |
| `INITIAL_WALLET_BALANCE` | 500000 | Starting virtual money (₹) |
| `MAX_TOPUP_AMOUNT` / `MAX_DAILY_TOPUPS` | 1000000 / 5 | Top-up limits |
| `MARKET_PROVIDER` | synthetic | `synthetic` or `yfinance` |
| `TICK_INTERVAL_MS` | 500 | Market update speed |
| `SIM_SEED` | 42 | Same seed = same market |
| `ARB_MIN_LATENCY_MS` / `ARB_MAX_LATENCY_MS` | 20 / 150 | Simulated arbitrage leg latency |
| `ARB_LEG_FAILURE_PROB` | 0.05 | Chance a leg fails |

## API overview

Base URL `/api/v1`. Every response uses `{ "success", "data", "error", "meta" }`. Send `Authorization: Bearer <token>` after logging in. Full reference: [docs/API.md](docs/API.md), or Swagger at `/docs`.

| Group | Main endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/change-password` |
| User | `GET/PATCH /users/me` |
| Wallet | `GET /wallet`, `GET /wallet/transactions`, `POST /wallet/topup`, `POST /wallet/reset` |
| Market | `GET /market/symbols`, `GET /market/quotes`, `GET /market/{symbol}/history`, `GET /market/{symbol}/{exchange}/depth` |
| Orders | `POST /orders`, `GET /orders`, `DELETE /orders/{id}`, `GET /trades`, `GET /trades/export.csv` |
| Portfolio | `GET /portfolio/summary`, `GET /portfolio/positions`, `GET /portfolio/equity-curve`, `GET /dashboard/profit`, `GET /dashboard/performance` |
| Strategies | `GET /strategies/types`, CRUD on `/strategies`, `POST /strategies/{id}/start`, `POST /strategies/{id}/stop` |
| Backtests | `POST /backtests`, `GET /backtests`, `GET /backtests/{id}` |
| Arbitrage | `GET /arbitrage/spreads`, `GET /arbitrage/opportunities`, `POST /arbitrage/execute`, `PUT /arbitrage/auto`, `GET /arbitrage/trades`, `GET /arbitrage/stats` |
| Risk | `GET/PUT /risk`, `POST /risk/kill-switch` |
| Admin | `GET /admin/users`, `PATCH /admin/users/{id}`, `POST /admin/users/{id}/wallet-adjust`, `GET /admin/metrics`, `GET /admin/audit-logs` |
| System | `GET /health`, `GET /metrics` |
| WebSockets | `/ws/market?token=` (ticks, depth, opportunities), `/ws/user?token=` (your orders, fills, wallet, arbitrage results) |

## Project structure

```
nanoex-web/
├── backend/
│   ├── app/
│   │   ├── api/v1/         routers (REST + WebSocket)
│   │   ├── services/       business logic
│   │   ├── repositories/   database access
│   │   ├── models/         SQLAlchemy tables
│   │   ├── schemas/        Pydantic models
│   │   ├── engine/         order book, matching engine, risk rules
│   │   ├── market/         synthetic + yfinance providers, streamer
│   │   ├── strategies/     9 strategies + factory
│   │   ├── indicators/     SMA, EMA, RSI, MACD, Bollinger, Z-score
│   │   ├── backtest/       backtester + metrics
│   │   ├── arbitrage/      cost model, detector, scanner, executor, auto bot
│   │   ├── bots/           live strategy bot runner
│   │   ├── core/           config, security, logging, event bus
│   │   ├── container.py    wires everything together
│   │   └── main.py         FastAPI app
│   ├── alembic/            migrations
│   ├── tests/              unit + integration
│   └── Dockerfile
├── frontend/
│   ├── src/ (pages, components, store, services, hooks, utils, test)
│   ├── nginx.conf
│   └── Dockerfile
├── docs/                   SRS, UML, Agile plan, test plan, risk/OWASP, API, manual, screenshots
├── docker-compose.yml
├── .github/workflows/ci.yml
└── .pre-commit-config.yaml
```

## Documentation

| Document | Contents |
|---|---|
| [SRS](docs/SRS.md) | Functional and non-functional requirements (IEEE 830 style) |
| [UML](docs/UML.md) | Use case, class, sequence (login, arbitrage), ER, component and deployment diagrams in Mermaid; PNG exports in [docs/diagrams](docs/diagrams) |
| [Architecture](docs/ARCHITECTURE.md) | Layers, design patterns, SOLID, key flows, improvements, future work |
| [Agile plan](docs/AGILE_PLAN.md) | Epics, 28 user stories, 4 sprints, Definition of Done |
| [Test plan](docs/TEST_PLAN.md) | Strategy and 76 test cases mapped to requirements, with results |
| [Risk & security](docs/RISK_AND_SECURITY.md) | Project risk register and OWASP Top 10 checklist |
| [API reference](docs/API.md) | Every endpoint and WebSocket message |
| [User manual](docs/USER_MANUAL.md) | How to use each page, charges table and FAQ |

## A note on arbitrage realism

Real NSE-BSE price gaps are usually a few paise and close within microseconds. They are captured by firms with co-located servers. After brokerage, STT, exchange fees, GST and stamp duty on two legs, a retail trader almost never profits. NanoEX shows this honestly: most spreads on the board are negative after costs. The simulator adds occasional larger dislocations, plus latency and leg-failure risk, so you can see how the strategy works and why it is hard.

## License

For educational use.
