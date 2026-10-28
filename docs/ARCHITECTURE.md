# Architecture and design notes: NanoEX Web

## 1. Style: modular monolith

One FastAPI process holds the API, the market simulator, 20 in-memory order books (10 stocks × NSE/BSE), the strategy bots and the arbitrage bot. Persistent state lives in PostgreSQL.

This is deliberate. Matching must be fast and consistent, and keeping the books in-process avoids network hops and distributed locking. Modules talk through interfaces and an event bus, so any of them could later move to its own service.

```
Browser (React SPA)
   │  REST /api/v1  +  WebSocket /ws
   ▼
Routers ──► Services ──► Repositories ──► SQLAlchemy models ──► PostgreSQL
               │
               ├─► Matching engine (order books, liquidity maker)
               ├─► Risk manager (8 rules)
               ├─► Arbitrage (scanner, detector, executor, auto bot)
               ├─► Bot runner (9 strategies)
               └─► Backtester
Market data service ── tick ──► engine, arbitrage scanner, bots ──► Event bus ──► WebSockets
```

## 2. Folder structure

```
backend/app/
  api/v1/        HTTP + WebSocket routers (thin: validate, call a service, wrap the response)
  services/      Use cases and transactions (auth, wallet, orders, portfolio, arbitrage, strategy, risk, admin)
  repositories/  Database queries, one class per aggregate
  models/        SQLAlchemy 2.0 tables (13)
  schemas/       Pydantic v2 request/response models
  engine/        Order book, matching engine, liquidity maker, risk rules
  market/        Data providers (synthetic, yfinance) and the tick streamer
  strategies/    9 strategies + factory + exits + live trader
  indicators/    SMA, EMA, RSI, MACD, Bollinger, Z-score (pure functions)
  backtest/      Data loader, runner, metrics
  arbitrage/     Cost model, detector, scanner, executor, auto bot
  bots/          Bot runner
  core/          Config, security, logging, errors, event bus, metrics, clock
  container.py   Composition root: builds and wires everything
frontend/src/
  pages/         One file per screen
  components/    ui/ (design system), layout/, charts/, trading/
  store/         Zustand stores (auth, market, account, toasts)
  services/      Axios client with refresh-on-401, WebSocket client
  hooks/         useApi, useStreams
```

## 3. Design patterns used

| Pattern | Where | Why |
|---|---|---|
| Layered architecture | routers → services → repositories | Each layer has one job; business rules never sit in routers |
| Repository | `app/repositories/` | Hides SQLAlchemy queries; services stay testable |
| Factory + Registry | `strategies/factory.py` (`@register`) | Add a strategy by writing one class; no switch statements |
| Strategy | `BaseStrategy` and its 9 subclasses; `MarketDataProvider` | Swap algorithms or data sources at runtime |
| Chain of Responsibility | `engine/risk/` (8 `RiskRule`s) | Each rule is independent; order and set are configurable |
| Observer / Pub-Sub | `core/event_bus.py` | Engine and services publish events; WebSockets and the scanner subscribe without coupling |
| Composite | Ensemble strategy | A strategy made of strategies that vote |
| Template Method | `BaseStrategy.update` → `evaluate` | Shared price history, warm-up and validation; each strategy writes only `evaluate` |
| Dependency Injection | FastAPI `Depends`, `Container` | Tests swap in a fixed-price provider and a fresh database |
| Singleton (via DI) | `get_settings()`, `Container` | One configuration and one engine per process |
| Value Object | `Quote`, `Opportunity`, `Signal`, `CostBreakdown`, `ChargeSchedule` (frozen dataclasses) | Immutable data passed between modules |

## 4. SOLID

- **S, single responsibility:** `OrderBook` only matches orders, `CostModel` only computes charges, `ArbitrageDetector` only finds opportunities, and `ArbitrageExecutor` only executes them.
- **O, open/closed:** new strategies, risk rules and data providers are added as new classes, without editing existing ones.
- **L, Liskov substitution:** any `MarketDataProvider` (synthetic, yfinance, or the test `StaticProvider`) works wherever a provider is expected.
- **I, interface segregation:** the detector depends on a tiny `Liquidity` protocol (`sweep_vwap`), not on the whole order book.
- **D, dependency inversion:** services receive their collaborators from the container, and high-level code depends on abstractions (`RiskRule`, `BaseStrategy`, `MarketDataProvider`).

## 5. Key flows

**Order placement** (`OrderService.place`):
1. Validate the symbol, tick size and price band.
2. Run the risk chain.
3. Block funds for buys.
4. Submit to the matching engine under a per-book asyncio lock.
5. Settle each fill: wallet ledger, position netting, realised P&L and charges.
6. Persist the order and its trades.
7. Publish events for the WebSockets.

**Market tick:** the provider produces quotes. The engine's liquidity maker re-quotes simulated depth around them, which can fill resting user orders. The arbitrage scanner evaluates spreads, and the auto bot may act. Bots get the new price, and a batched `tick` event reaches the browsers.

**Arbitrage:** see the sequence diagram in [UML.md](UML.md#4-sequence-diagram-nse-bse-arbitrage-execution).

## 6. Money and correctness rules
- Money is stored as `Numeric(18,2)` and prices as `Numeric(14,4)`. Python uses `Decimal` for all of it, and floats appear only in JSON responses.
- Every balance change appends to `wallet_transactions` with `balance_after`.
- Profit = equity − capital added, so top-ups and admin credits never appear as profit.
- Positions are netted per stock across exchanges, the way a demat account works. That is what makes a buy on NSE plus a sell on BSE end flat.

## 7. Improvements over the original brief

These were suggested and built in:

| Area | Original idea | What was built and why |
|---|---|---|
| Wallet | Fixed starting money | ₹5 L start, top-ups, reset when flat, and an append-only ledger. Profit is measured against capital added, so top-ups can't fake returns |
| Profit view | General dashboard | A dedicated Profit & Portfolio page with P&L split by strategy, stock and source (manual, bots, arbitrage) |
| Arbitrage | Detect and trade the NSE-BSE gap | Liquidity-aware detection (VWAP sweep, not just top of book), full Indian charges on both legs, simulated latency and leg failure, automatic hedging of a failed leg, honest "reality check" note |
| Order book | Simple matching | Price-time priority with self-trade prevention, plus a liquidity maker so user limit orders fill realistically |
| Auth | JWT | Short access token in memory only, httpOnly refresh cookie with rotation and reuse detection, rate limiting, audit trail |
| Strategies | A few strategies | Nine strategies through one factory, with SL/TP/trailing exits and a recorded reason on every order |
| Backtesting | Basic P&L | Same cost model as live trading, buy-and-hold comparison, Sharpe/Sortino/drawdown/profit factor, reproducible seeds |
| Ops | — | Docker compose with Postgres, CI, pre-commit, health checks, Prometheus metrics, production secret check |

## 8. Future work
- Move the matching engine to its own process with Redis or NATS for events, so the API can scale horizontally.
- Add intraday candles (OHLC) and candlestick charts.
- Add F&O instruments with margin (SPAN-like) rules.
- Add a leaderboard and classroom mode, where a teacher creates a cohort and compares students.
- Add a one-time ticket for WebSocket auth instead of a query-string token.
- Add `pip-audit` and `npm audit` to CI.
