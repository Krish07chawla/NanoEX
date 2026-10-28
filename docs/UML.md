# UML diagrams: NanoEX Web

All diagrams are in Mermaid, so they render on GitHub, GitLab and in VS Code (with a Mermaid extension). Paste any block into <https://mermaid.live> to export it as PNG or SVG for a report.

## 1. Use case diagram

Mermaid has no native use-case notation, so actors are drawn as nodes and use cases as rounded boxes inside the system boundary.

```mermaid
flowchart LR
    guest(["👤 Guest"])
    trader(["👤 Trader"])
    admin(["👤 Admin"])
    market(["⏱ Market simulator<br/>(system actor)"])

    subgraph NanoEX["NanoEX Web"]
        UC1([Register])
        UC2([Log in / log out])
        UC3([View live market and depth])
        UC4([Place / cancel order])
        UC5([Manage wallet: top up, reset])
        UC6([Configure and run strategy bot])
        UC7([Run backtest])
        UC8([View NSE-BSE spreads])
        UC9([Execute arbitrage manually])
        UC10([Enable auto arbitrage])
        UC11([Set risk limits / kill switch])
        UC12([View profit and portfolio dashboard])
        UC13([View and export trade history])
        UC14([Manage users and wallets])
        UC15([View system metrics and audit log])
        UC16([Match orders and stream prices])
        UC17([Pre-trade risk check])
    end

    guest --- UC1 & UC2
    trader --- UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC13
    admin --- UC14 & UC15
    admin -. "inherits Trader" .- trader
    market --- UC16
    UC4 -. "«include»" .-> UC17
    UC9 -. "«include»" .-> UC17
    UC10 -. "«extend»" .-> UC9
    UC6 -. "«include»" .-> UC17
```

## 2. Class diagram (core domain)

```mermaid
classDiagram
    direction LR

    class OrderBook {
        +symbol: str
        +exchange: str
        +best_bid() Decimal
        +best_ask() Decimal
        +submit(order) MatchResult
        +cancel(order_id) BookOrder
        +depth(levels) dict
        +sweep_vwap(side, qty) tuple
        -_match(order, result)
        -_rest(order)
    }
    class MatchingEngine {
        -books: dict
        -locks: dict
        +submit(symbol, exchange, order) MatchResult
        +cancel(symbol, exchange, id)
        +on_quotes(quotes)
        +depth(symbol, exchange)
    }
    class LiquidityMaker {
        +quotes_for(quote) list~BookOrder~
    }
    class BookOrder {
        +id: str
        +user_id: str
        +side: Side
        +price: Decimal
        +quantity: int
        +remaining: int
    }
    MatchingEngine "1" *-- "20" OrderBook : one per symbol × exchange
    MatchingEngine --> LiquidityMaker
    OrderBook "1" o-- "*" BookOrder

    class RiskRule {
        <<abstract>>
        +check(ctx) raises RiskLimitExceeded
    }
    class RiskManager {
        -rules: list~RiskRule~
        +check(ctx) runs every rule
    }
    RiskManager o-- RiskRule : chain of responsibility
    RiskRule <|-- KillSwitchRule
    RiskRule <|-- MaxOrderQtyRule
    RiskRule <|-- MaxOrderNotionalRule
    RiskRule <|-- MaxOpenOrdersRule
    RiskRule <|-- MaxPositionValueRule
    RiskRule <|-- DailyLossLimitRule
    RiskRule <|-- DailyVolumeCapRule
    RiskRule <|-- FundsRule

    class BaseStrategy {
        <<abstract>>
        +key: str
        +params: dict
        +update(price) Signal
        +evaluate(prices) Signal
        +validate()
    }
    class StrategyFactory {
        +register(cls)$
        +create(key, params) BaseStrategy
        +available() list~dict~
    }
    StrategyFactory ..> BaseStrategy : creates
    BaseStrategy <|-- Momentum
    BaseStrategy <|-- MeanReversion
    BaseStrategy <|-- Breakout
    BaseStrategy <|-- EmaCrossover
    BaseStrategy <|-- MacdCrossover
    BaseStrategy <|-- RsiReversal
    BaseStrategy <|-- BollingerBands
    BaseStrategy <|-- ZScore
    BaseStrategy <|-- Ensemble
    Ensemble o-- BaseStrategy : votes

    class MarketDataProvider {
        <<interface>>
        +next_quotes() list~Quote~
        +symbols() list~str~
    }
    MarketDataProvider <|.. SyntheticProvider
    MarketDataProvider <|.. YFinanceProvider

    class CostModel {
        +leg_costs(exchange, side, price, qty) CostBreakdown
        +round_trip(...) CostBreakdown
    }
    class ArbitrageDetector {
        +evaluate(symbol, books, qty) Opportunity
    }
    class ArbitrageExecutor {
        +execute(session, user_id, symbol, qty, mode) ArbitrageTrade
        -_plan_legs(opp)
        -_send_leg(leg)
        -_flatten(...)
    }
    class AutoArbitrageBot
    class OrderService {
        +place(user, request) Order
        +cancel(user, order_id)
    }
    ArbitrageDetector --> CostModel
    ArbitrageExecutor --> OrderService : both legs
    AutoArbitrageBot --> ArbitrageDetector
    AutoArbitrageBot --> ArbitrageExecutor
    OrderService --> RiskManager
    OrderService --> MatchingEngine
    OrderService --> SettlementService
    BotRunner --> StrategyTrader
    StrategyTrader --> BaseStrategy
    StrategyTrader --> OrderService
```

## 3. Sequence diagram: login and token refresh

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as React app
    participant API as FastAPI /auth
    participant RL as Rate limiter
    participant AS as AuthService
    participant DB as Database

    U->>FE: Enter email + password
    FE->>API: POST /api/v1/auth/login
    API->>RL: check 5/min per IP
    RL-->>API: allowed
    API->>AS: login(email, password)
    AS->>DB: SELECT user by email
    DB-->>AS: user row
    AS->>AS: bcrypt.verify (dummy hash if no user, constant time)
    alt invalid credentials or disabled
        AS->>DB: audit LOGIN_FAILED
        AS-->>API: AuthError
        API-->>FE: 401 {success:false, error}
        FE-->>U: "Invalid email or password"
    else valid
        AS->>DB: INSERT refresh_token (jti, expires_at)
        AS->>DB: audit LOGIN
        AS-->>API: access JWT (15 min) + refresh token
        API-->>FE: 200 {access_token, user} + Set-Cookie (httpOnly, SameSite=Strict)
        FE->>FE: keep access token in memory (Zustand)
        FE-->>U: redirect to dashboard
    end

    Note over FE,API: Later, an API call returns 401 because the access token expired
    FE->>API: POST /api/v1/auth/refresh (cookie sent automatically)
    API->>AS: rotate(refresh)
    AS->>DB: verify JWT, find token by jti
    alt token already used (reuse)
        AS->>DB: revoke every token of this user
        API-->>FE: 401, user must log in again
    else valid
        AS->>DB: revoke old jti, insert new one
        API-->>FE: new access token + new cookie
        FE->>API: retry the original request once
    end
```

## 4. Sequence diagram: NSE-BSE arbitrage execution

```mermaid
sequenceDiagram
    autonumber
    actor U as Trader (or Auto bot)
    participant API as /arbitrage/execute
    participant DET as ArbitrageDetector
    participant CM as CostModel
    participant EX as ArbitrageExecutor
    participant OS as OrderService
    participant RM as RiskManager
    participant ME as MatchingEngine
    participant DB as Database
    participant WS as WebSocket

    U->>API: execute {symbol, quantity}
    API->>DET: evaluate(symbol, NSE book, BSE book, qty)
    DET->>DET: sweep_vwap: buy side on cheaper exchange, sell side on dearer
    DET->>CM: round-trip costs (brokerage, STT, exch, SEBI, GST, stamp, slippage)
    CM-->>DET: costs
    alt net profit < threshold
        DET-->>API: no opportunity
        API-->>U: 409 NO_OPPORTUNITY (with spread and cost breakdown)
    else profitable
        DET-->>EX: Opportunity(buy NSE @a, sell BSE @b)
        EX->>DB: check available cash for buy leg
        EX->>EX: plan legs: random latency 20-150 ms, 5% failure chance each
        par legs in latency order
            EX->>OS: BUY market on cheaper exchange (after latency)
            OS->>RM: pre-trade checks
            RM-->>OS: pass
            OS->>ME: submit
            ME-->>OS: fills
            OS->>DB: orders, trades, wallet, position (tagged arbitrage_trade_id)
        and
            EX->>OS: SELL market on dearer exchange (after latency)
            OS->>RM: pre-trade checks
            OS->>ME: submit
            ME-->>OS: fills
            OS->>DB: persist
        end
        alt both legs filled
            EX->>EX: status COMPLETED
        else one leg failed or partial
            EX->>OS: flatten unmatched quantity at market
            EX->>EX: status HEDGED / PARTIAL / FAILED
        end
        EX->>DB: P&L from actual fills, latency, charges
        EX->>WS: arb_result, order_update, wallet
        EX-->>API: ArbitrageTrade
        API-->>U: 200 result
    end
```

## 5. ER diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--|| WALLETS : owns
    WALLETS ||--o{ WALLET_TRANSACTIONS : records
    USERS ||--o{ ORDERS : places
    ORDERS ||--o{ TRADES : "fills into"
    USERS ||--o{ TRADES : makes
    USERS ||--o{ POSITIONS : holds
    USERS ||--o{ STRATEGIES_CONFIG : configures
    STRATEGIES_CONFIG ||--o{ ORDERS : generates
    USERS ||--o{ BACKTEST_RESULTS : runs
    USERS ||--o{ ARBITRAGE_TRADES : executes
    ARBITRAGE_OPPORTUNITIES |o--o{ ARBITRAGE_TRADES : "acted on by"
    ARBITRAGE_TRADES ||--o{ ORDERS : "two legs"
    USERS ||--|| RISK_SETTINGS : has
    USERS ||--o{ AUDIT_LOGS : "actor of"

    USERS {
        string id PK
        string email UK
        string password_hash
        string full_name
        string role "USER | ADMIN"
        bool is_active
        datetime created_at
        datetime last_login_at
    }
    REFRESH_TOKENS {
        string id PK
        string user_id FK
        string jti UK
        datetime expires_at
        datetime revoked_at
    }
    WALLETS {
        string id PK
        string user_id FK,UK
        decimal balance
        decimal blocked_margin
        decimal initial_balance
        decimal capital_added
    }
    WALLET_TRANSACTIONS {
        string id PK
        string wallet_id FK
        string type "INITIAL|TOPUP|RESET|TRADE_DEBIT|TRADE_CREDIT|FEE|ADMIN_ADJUST"
        decimal amount
        decimal balance_after
        string reference_id
        string note
        datetime created_at
    }
    ORDERS {
        string id PK
        string user_id FK
        string symbol
        string exchange "NSE | BSE"
        string side "BUY | SELL"
        string order_type "MARKET | LIMIT"
        decimal price
        int quantity
        int filled_qty
        decimal avg_fill_price
        string status
        string source "MANUAL|STRATEGY|ARBITRAGE"
        string strategy_config_id FK
        string arbitrage_trade_id FK
        decimal blocked_amount
        string strategy_name
        string signal_reason
        string reject_reason
        int latency_us
    }
    TRADES {
        string id PK
        string order_id FK
        string user_id FK
        string symbol
        string exchange
        string side
        decimal price
        int quantity
        decimal fees
        decimal realized_pnl
        string source
        datetime executed_at
    }
    POSITIONS {
        string id PK
        string user_id FK
        string symbol "UK(user_id, symbol)"
        int quantity
        decimal avg_price
        decimal realized_pnl
    }
    STRATEGIES_CONFIG {
        string id PK
        string user_id FK
        string name
        string strategy_type
        string symbol
        string exchange
        json params
        int quantity
        decimal stop_loss_pct
        decimal take_profit_pct
        decimal trailing_stop_pct
        bool is_active
    }
    BACKTEST_RESULTS {
        string id PK
        string user_id FK
        string strategy_type
        json params
        string symbol
        string data_source
        int bars
        int seed
        decimal initial_capital
        json metrics
        json equity_curve
        json trades
    }
    ARBITRAGE_OPPORTUNITIES {
        string id PK
        string symbol
        string buy_exchange
        string sell_exchange
        decimal buy_price
        decimal sell_price
        decimal spread_abs
        decimal spread_pct
        int quantity
        decimal est_costs
        decimal est_net_profit
        bool liquidity_ok
        datetime detected_at
    }
    ARBITRAGE_TRADES {
        string id PK
        string user_id FK
        string opportunity_id FK
        string symbol
        string buy_exchange
        string sell_exchange
        int quantity
        int matched_qty
        string mode "MANUAL|AUTO"
        string buy_order_id
        string sell_order_id
        decimal expected_spread
        decimal captured_spread
        string status "COMPLETED|PARTIAL|HEDGED|FAILED"
        decimal gross_pnl
        decimal total_costs
        decimal net_pnl
        int latency_ms
        string failure_reason
    }
    RISK_SETTINGS {
        string id PK
        string user_id FK,UK
        int max_order_qty
        decimal max_order_notional
        decimal max_position_value
        decimal daily_loss_limit
        decimal daily_volume_cap
        int max_open_orders
        bool kill_switch
        decimal arb_min_profit
        int arb_quantity
        bool arb_auto_enabled
    }
    AUDIT_LOGS {
        string id PK
        string user_id FK
        string action
        string entity
        string entity_id
        string ip_address
        string user_agent
        json details
        datetime created_at
    }
```

Every table also has `id` (UUID string), `created_at` and `updated_at`. Source of truth: `backend/app/models/` and `backend/alembic/versions/0001_initial_schema.py`.

## 6. Component diagram

```mermaid
flowchart TB
    subgraph Browser["Browser: React + TypeScript (Vite)"]
        Pages["Pages<br/>Dashboard · Profit · Market · Arbitrage<br/>Strategies · Backtester · Portfolio · Admin"]
        Stores["Zustand stores<br/>auth · market · account · toasts"]
        ApiClient["Axios client<br/>(auto refresh on 401)"]
        WsClient["WebSocket client<br/>(auto reconnect)"]
        Pages --> Stores
        Pages --> ApiClient
        WsClient --> Stores
    end

    subgraph Backend["FastAPI backend (single process)"]
        Routers["API routers /api/v1<br/>+ /ws/market, /ws/user"]
        Services["Services<br/>Auth · Wallet · Order · Portfolio<br/>Strategy · Arbitrage · Risk · Admin"]
        Repos["Repositories (SQLAlchemy 2.0)"]
        subgraph Domain["Domain engine"]
            Market["Market data service<br/>Synthetic / yfinance"]
            Engine["Matching engine<br/>20 order books"]
            Risk["Risk manager<br/>8 rules"]
            Arb["Arbitrage<br/>scanner · detector · executor · auto bot"]
            Bots["Bot runner<br/>9 strategies"]
            Backtest["Backtester"]
        end
        Bus["Event bus (asyncio pub/sub)"]
        Container["Container<br/>(composition root)"]

        Routers --> Services --> Repos
        Services --> Engine & Risk & Arb & Backtest
        Market -- tick --> Engine
        Market -- tick --> Arb
        Market -- tick --> Bots
        Engine & Arb & Services -- events --> Bus
        Bus --> Routers
        Container -. wires .-> Services & Domain
    end

    DB[("PostgreSQL 16<br/>(SQLite in dev)")]
    YF["Yahoo Finance<br/>(optional)"]

    ApiClient -- "REST JSON" --> Routers
    WsClient -- "WebSocket" --> Routers
    Repos --> DB
    Market -. optional .-> YF
```

## 7. Deployment diagram

```mermaid
flowchart LR
    user["💻 User's browser"]
    subgraph Host["Docker host (docker compose)"]
        subgraph fe["container: frontend"]
            nginx["nginx 1.27<br/>serves React build<br/>proxies /api, /ws, /health"]
        end
        subgraph be["container: backend"]
            uvicorn["uvicorn + FastAPI<br/>(1 worker)<br/>runs alembic upgrade on start"]
        end
        subgraph db["container: db"]
            pg[("postgres:16-alpine")]
            vol[["volume: pgdata"]]
        end
    end
    user -- "HTTP :8080" --> nginx
    nginx -- "HTTP / WS :8000" --> uvicorn
    uvicorn -- "asyncpg :5432" --> pg
    pg --- vol
```

Only port 8080 is published. The database and backend are reachable only on the internal Docker network. In production, put a TLS terminator (for example Caddy or a cloud load balancer) in front of nginx and set `COOKIE_SECURE=true`.
