# Agile plan: NanoEX Web

Method: Scrum, four two-week sprints (8 weeks). Team roles for a student team of 3-4: Product Owner (also a developer), Scrum Master, developers. Story points use the Fibonacci scale (1, 2, 3, 5, 8, 13).

**Ceremonies:** sprint planning (Monday, 1 h), daily stand-up (15 min, can be async on chat), sprint review with a demo (last Friday), retrospective (30 min, right after the review).

**Definition of Done:** code reviewed by one teammate; unit/integration tests written and passing; ruff, black, eslint and prettier clean; CI green; API docs and the user manual updated when behaviour changes; demoable on `docker compose up`.

## Epics

| ID | Epic | Goal |
|---|---|---|
| E1 | Accounts and security | Users can register and log in safely; admins have extra powers |
| E2 | Wallet | A ₹5 L paper wallet that can be topped up, with a ledger |
| E3 | Market and matching | Live simulated NSE/BSE market with real order books |
| E4 | Trading | Manual orders, positions, P&L, trade history |
| E5 | Strategies and backtesting | Nine strategies as bots and in a backtester with Indian costs |
| E6 | NSE-BSE arbitrage | Detect spreads and execute two-leg trades, manual and auto |
| E7 | Risk management | Pre-trade checks and a kill switch |
| E8 | Dashboards and admin | Profit/portfolio dashboard, performance metrics, admin pages |
| E9 | Quality and delivery | Tests, CI, Docker, documentation |

## Product backlog (user stories)

| ID | Epic | User story | Acceptance criteria | Pts | Sprint |
|---|---|---|---|---|---|
| US-01 | E1 | As a guest, I want to register so that I get my own paper account | Valid email, strong password; duplicate email rejected; wallet created | 3 | 1 |
| US-02 | E1 | As a user, I want to log in and stay logged in so that I don't retype my password | 15-min access token, refresh cookie, silent refresh | 5 | 1 |
| US-03 | E1 | As a user, I want stolen refresh tokens to stop working so that my account is safe | Reuse of a rotated token revokes all sessions | 3 | 1 |
| US-04 | E1 | As an admin, I want admin-only pages so that normal users can't manage others | 403 for non-admins | 2 | 1 |
| US-05 | E2 | As a trader, I want ₹5,00,000 to start with so that I can trade straight away | New wallet shows ₹5,00,000 | 1 | 1 |
| US-06 | E2 | As a trader, I want to top up my wallet so that I can keep practising | Limits enforced; top-up counted as capital, not profit | 3 | 1 |
| US-07 | E3 | As a trader, I want live NSE and BSE prices so that the market feels real | Quotes update every 500 ms over WebSocket | 5 | 1 |
| US-08 | E3 | As a trader, I want to see market depth so that I understand liquidity | 10 levels each side with order counts | 3 | 2 |
| US-09 | E3 | As a learner, I want a real price-time priority order book so that I learn how matching works | Unit tests for priority, partial fills, self-trade prevention | 8 | 2 |
| US-10 | E4 | As a trader, I want to place market and limit orders so that I can trade | Market fills immediately; limit rests and fills later | 5 | 2 |
| US-11 | E4 | As a trader, I want to cancel an open order so that blocked funds are released | Funds released, status CANCELLED | 2 | 2 |
| US-12 | E4 | As a trader, I want my positions and P&L so that I know how I'm doing | Avg price, realised and unrealised P&L, charges | 5 | 2 |
| US-13 | E7 | As a trader, I want pre-trade risk checks so that one mistake can't wipe me out | 8 rules, rejection reason saved | 5 | 2 |
| US-14 | E7 | As a trader, I want a kill switch so that I can stop everything at once | Blocks orders, cancels open orders, stops bots | 3 | 2 |
| US-15 | E5 | As a learner, I want nine ready-made strategies so that I can compare them | Factory lists 9 with parameter schemas | 8 | 3 |
| US-16 | E5 | As a trader, I want to run a strategy as a live bot so that it trades for me | Start/stop; orders carry signal reason; SL/TP/trailing | 5 | 3 |
| US-17 | E5 | As a learner, I want to backtest with Indian charges so that results are realistic | Brokerage, STT, exchange, SEBI, GST, stamp, slippage; same seed same result | 8 | 3 |
| US-18 | E6 | As a trader, I want to see the NSE-BSE price gap for each stock so that I can spot arbitrage | Live spreads table, net after costs | 3 | 3 |
| US-19 | E6 | As a trader, I want to execute an arbitrage with one click so that both legs go out together | Buy cheaper + sell dearer; status and P&L shown | 8 | 3 |
| US-20 | E6 | As a trader, I want auto arbitrage above my threshold so that I don't miss gaps | Threshold and quantity; cooldown; respects kill switch | 5 | 3 |
| US-21 | E6 | As a learner, I want leg risk simulated so that I learn why real arbitrage is hard | Latency, 5% leg failure, hedge flatten | 5 | 3 |
| US-22 | E8 | As a trader, I want a profit dashboard so that I see only my results | Total profit, equity curve, P&L by strategy/symbol/source | 5 | 4 |
| US-23 | E4 | As a trader, I want to export my trades to CSV so that I can analyse them in Excel | CSV with all fills and charges | 2 | 4 |
| US-24 | E8 | As a trader, I want performance stats so that I see HFT-style metrics | Orders/sec, avg latency, tick-to-trade | 3 | 4 |
| US-25 | E8 | As an admin, I want to manage users and wallets so that I can run a class | Disable, role change, wallet adjust, audit log | 5 | 4 |
| US-26 | E9 | As a developer, I want CI so that broken code never merges | Lint, tests, build, Docker on every push | 3 | 4 |
| US-27 | E9 | As an evaluator, I want SE documents so that I can grade the process | SRS, UML, Agile plan, test plan, risk + OWASP | 5 | 4 |
| US-28 | E9 | As a user, I want to start everything with one command | `docker compose up` works | 3 | 4 |

## Sprint plan

| Sprint | Weeks | Goal | Stories | Points |
|---|---|---|---|---|
| 1 | 1-2 | Users can sign up, log in, see a funded wallet and live prices | US-01 to US-07 | 22 |
| 2 | 3-4 | Users can trade on a real order book, safely | US-08 to US-14 | 31 |
| 3 | 5-6 | Strategies, backtests and NSE-BSE arbitrage work end to end | US-15 to US-21 | 42 |
| 4 | 7-8 | Dashboards, admin, CI, Docker and documents are done | US-22 to US-28 | 26 |

Sprint 3 is the heaviest. If velocity after Sprint 2 is below 30, move US-21 (leg-risk simulation) and US-20 (auto mode) to Sprint 4 and drop US-24 to "could have".

## Sprint 1 task breakdown (example)

| Task | Story | Estimate (h) |
|---|---|---|
| Set up FastAPI project, config, logging, response envelope | US-01 | 4 |
| Users, wallets, refresh_tokens models + Alembic migration | US-01 | 4 |
| bcrypt hashing, JWT issue/verify | US-02 | 3 |
| Refresh rotation and reuse detection + tests | US-03 | 4 |
| Role dependency and admin guard | US-04 | 2 |
| Wallet service, ledger, top-up limits + tests | US-05, US-06 | 5 |
| Synthetic market provider (GBM + basis) | US-07 | 6 |
| WebSocket /ws/market | US-07 | 3 |
| React skeleton, auth store, login/register pages | US-01, US-02 | 8 |

## Burndown tracking

Track remaining story points at each stand-up in a simple sheet. Ideal line for Sprint 1: 22 → 0 over 10 working days (2.2 pts/day).

## Risks to the plan

| Risk | Mitigation |
|---|---|
| Matching engine bugs block trading features | Build and unit-test the order book first in Sprint 2 |
| Async/SQLite locking issues | WAL mode, short transactions, Postgres in Docker |
| Scope creep (more strategies, F&O) | Product Owner guards the backlog; extras go to "future work" |
| Team member unavailable | Pair on the engine and arbitrage modules so two people know them |
