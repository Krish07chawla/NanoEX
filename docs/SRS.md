# Software Requirements Specification: NanoEX Web

Version 1.0 · 27 Oct 2026 · Format based on IEEE 830

> NanoEX Web is an educational simulation. All trading is paper trading with virtual money. It never places a real order with any broker or exchange, and nothing in it is financial advice.

## 1. Introduction

### 1.1 Purpose
This document states what NanoEX Web must do and the qualities it must have. It is written for the project team, the course evaluator and anyone extending the system.

### 1.2 Scope
NanoEX Web is a browser-based paper-trading simulator for the Indian equity market (NSE and BSE). It teaches how high-frequency and algorithmic trading work: a limit order book, a matching engine, rule-based strategies, backtesting with real Indian charges, cross-exchange arbitrage and pre-trade risk control. Each user gets a virtual wallet of ₹5,00,000 that they can top up.

Out of scope: real-money trading, broker integration, derivatives (F&O), intraday leverage beyond a simple short-sale margin, mobile apps.

### 1.3 Definitions
| Term | Meaning |
|---|---|
| Paper trading | Simulated trading with virtual money |
| LOB | Limit order book: resting buy and sell orders at each price |
| Matching engine | Component that pairs buy and sell orders by price-time priority |
| Arbitrage | Buying a stock on the cheaper exchange and selling it on the dearer one at the same time |
| Leg | One side (buy or sell) of an arbitrage trade |
| Leg risk | Risk that one leg fills and the other does not |
| Kill switch | A control that blocks all new orders and cancels open ones |
| STT | Securities Transaction Tax |
| Tick size | Smallest price step, ₹0.05 |
| Capital added | Starting balance plus top-ups; profit is measured against it |

### 1.4 References
SEBI and NSE/BSE published charge schedules (2024-25), OWASP Top 10 (2021), IEEE 830-1998.

## 2. Overall description

### 2.1 Product perspective
A self-contained web application: a React single-page app talks to a FastAPI backend over REST and WebSockets. The backend owns a simulated market (one order book per stock per exchange), persists users, orders, trades and wallets in PostgreSQL (SQLite in development), and runs strategies and the arbitrage bot in-process.

### 2.2 User classes
| Class | Description |
|---|---|
| Guest | Can view the landing page, register and log in |
| Trader (USER) | Trades, runs strategies and backtests, uses arbitrage, manages wallet and risk limits |
| Administrator (ADMIN) | Everything a trader can do, plus manage users, adjust wallets, view system metrics and audit logs |

### 2.3 Operating environment
Modern desktop browser (Chrome, Firefox, Edge, Safari). Server: Python 3.12, PostgreSQL 16, or Docker. Works fully offline with the synthetic market; the optional yfinance provider needs internet access.

### 2.4 Constraints
- Paper trading only. No code path sends orders outside the process.
- Secrets come from environment variables only.
- One backend worker process, because the order books live in memory.

### 2.5 Assumptions
Market hours are not enforced, so the simulator runs any time. Prices are synthetic unless yfinance is selected.

## 3. Functional requirements

Priority: **M** = must, **S** = should, **C** = could.

### 3.1 Authentication and users
| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | A guest can register with name, email and password (8+ characters, at least one letter and one number) | M |
| FR-1.2 | A user can log in and receive a 15-minute access token and a 7-day refresh token in an httpOnly cookie | M |
| FR-1.3 | Refresh tokens rotate on every use; reusing an old token revokes all of that user's sessions (theft detection) | M |
| FR-1.4 | A user can log out, which revokes the refresh token | M |
| FR-1.5 | A user can change their password and update their profile | S |
| FR-1.6 | Login and register are rate limited (5 per minute per IP) | M |
| FR-1.7 | Two roles exist: USER and ADMIN. Admin routes reject non-admins with 403 | M |

### 3.2 Wallet
| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Every new user receives a ₹5,00,000 virtual wallet | M |
| FR-2.2 | A user can top up the wallet (max ₹10,00,000 per top-up, 5 per day) | M |
| FR-2.3 | Top-ups increase "capital added", so they never show as profit | M |
| FR-2.4 | A user can reset the wallet to ₹5,00,000 only when they hold no positions or open orders | S |
| FR-2.5 | Every balance change is written to an append-only ledger | M |
| FR-2.6 | Funds for open buy orders are blocked until the order fills or is cancelled | M |

### 3.3 Market data
| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | The system streams quotes for 10 NSE/BSE stocks every 500 ms | M |
| FR-3.2 | NSE and BSE prices for a stock stay close but differ by a small, mean-reverting basis, with occasional dislocations | M |
| FR-3.3 | The market is reproducible from a seed | S |
| FR-3.4 | An optional yfinance provider uses real historical prices | C |
| FR-3.5 | Users can view live quotes, price history and 10-level market depth | M |

### 3.4 Orders and matching
| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | A user can place MARKET and LIMIT orders, BUY or SELL, on NSE or BSE | M |
| FR-4.2 | Orders match by price-time priority; trades execute at the resting order's price | M |
| FR-4.3 | Market orders are immediate-or-cancel; any unfilled quantity is cancelled | M |
| FR-4.4 | Limit orders rest in the book and fill later when the market reaches them | M |
| FR-4.5 | A user can cancel an open order | M |
| FR-4.6 | Self-trade prevention stops a user trading with their own order | S |
| FR-4.7 | Limit prices must be within ±20% of the last price and on the ₹0.05 tick | S |

### 3.5 Strategies and bots
| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Nine strategies are available: Momentum, Mean Reversion, Breakout, EMA Crossover, MACD Crossover, RSI Reversal, Bollinger Bands, Z-Score, Ensemble Vote | M |
| FR-5.2 | A user can create, edit, start, stop and delete a strategy bot with its own parameters | M |
| FR-5.3 | Parameters are validated (ranges and cross-rules such as fast < slow) | M |
| FR-5.4 | Bots support stop-loss, take-profit and trailing-stop exits | S |
| FR-5.5 | Every bot order records the reason for its signal | S |

### 3.6 Backtesting
| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | A user can backtest any strategy on synthetic or yfinance daily data | M |
| FR-6.2 | Every simulated trade pays brokerage, STT, exchange charges, SEBI fee, GST, stamp duty and slippage | M |
| FR-6.3 | Results show total return, buy-and-hold return, max drawdown, Sharpe, Sortino, win rate, profit factor, trade list and equity curve | M |
| FR-6.4 | The same seed gives the same result | M |
| FR-6.5 | Backtest results are saved and can be reopened | S |

### 3.7 NSE-BSE arbitrage
| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | The system shows the live price difference for each stock between NSE and BSE | M |
| FR-7.2 | It lists opportunities where the spread exceeds all costs, with buy exchange, sell exchange, estimated costs, net profit and available liquidity | M |
| FR-7.3 | A user can execute an opportunity manually: a BUY on the cheaper exchange and a SELL on the dearer one | M |
| FR-7.4 | Auto mode executes the best opportunity above the user's minimum net profit, with a per-symbol cooldown | M |
| FR-7.5 | Each leg has simulated latency (20-150 ms) and a 5% failure chance | M |
| FR-7.6 | If one leg fails, the filled leg is closed at market and the result is marked HEDGED | M |
| FR-7.7 | The page explains honestly that real retail NSE-BSE arbitrage is rarely profitable | M |
| FR-7.8 | Arbitrage statistics show cumulative net P&L, hit rate, average spread and latency | S |

### 3.8 Risk management
| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Every order passes pre-trade checks: kill switch, max order quantity, max order value, max open orders, max position value, daily loss limit, daily volume cap, funds | M |
| FR-8.2 | A user can edit their own limits | M |
| FR-8.3 | The kill switch blocks new orders, cancels open orders and stops bots | M |
| FR-8.4 | Rejected orders are saved with the reason | M |
| FR-8.5 | Short selling needs 20% margin | S |

### 3.9 Portfolio, history and analytics
| ID | Requirement | Priority |
|---|---|---|
| FR-9.1 | Positions are netted per stock across both exchanges (like a demat account) | M |
| FR-9.2 | A Profit & Portfolio dashboard shows total profit, realised and unrealised P&L, charges, win rate, equity curve, daily P&L and P&L by strategy, by symbol and by source | M |
| FR-9.3 | Trade history is filterable and pageable and can be exported to CSV | M |
| FR-9.4 | A performance panel shows orders per second, average order latency and tick-to-trade time | S |

### 3.10 Administration
| ID | Requirement | Priority |
|---|---|---|
| FR-10.1 | An admin can list users, disable/enable them and change roles | M |
| FR-10.2 | An admin can credit or debit a user's wallet with a reason | S |
| FR-10.3 | An admin can view system metrics and the audit log | M |
| FR-10.4 | Security-relevant actions (login, logout, top-up, kill switch, admin actions) are audited | M |

## 4. Non-functional requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | Order placement round trip (risk + match + settle) under 50 ms on a laptop; the measured average is about 19 ms |
| NFR-2 | Performance | Market updates reach the browser within one tick (500 ms) |
| NFR-3 | Security | Passwords hashed with bcrypt (12 rounds); JWT secrets from environment; production refuses to start with a weak secret |
| NFR-4 | Security | Access token in memory only; refresh token in an httpOnly, SameSite=Strict cookie scoped to /api/v1/auth |
| NFR-5 | Security | Input validated with Pydantic; ORM-only database access (no raw SQL with user input) |
| NFR-6 | Reliability | Money stored as fixed-point decimals (Numeric 18,2), never floats |
| NFR-7 | Reliability | Open orders are restored into the books after a restart |
| NFR-8 | Usability | Dark trading-terminal theme; a "PAPER TRADING · SIMULATION" badge on every screen; disclaimer on login and footer |
| NFR-9 | Maintainability | Layered architecture (routers → services → repositories → models); ruff + black + eslint + prettier; backend coverage ≥ 80% (currently 88%) |
| NFR-10 | Portability | Runs with `docker compose up` or locally with SQLite |
| NFR-11 | Observability | Structured JSON logs with request ids; `/health` and Prometheus-style `/metrics` |

## 5. External interfaces
- **User interface:** React SPA; see [USER_MANUAL.md](USER_MANUAL.md) and the screenshots in the README.
- **REST API:** JSON over HTTPS under `/api/v1`, one response envelope `{success, data, error, meta}`; see [API.md](API.md).
- **WebSockets:** `/ws/market` (quotes, depth) and `/ws/user?token=` (order updates, trades, wallet, arbitrage results).
- **Database:** PostgreSQL 16 via SQLAlchemy 2.0 async; schema managed by Alembic.

## 6. Acceptance criteria
The system is accepted when every **M** requirement is covered by a passing test case in [TEST_PLAN.md](TEST_PLAN.md), CI is green, and the app runs with `docker compose up`.
