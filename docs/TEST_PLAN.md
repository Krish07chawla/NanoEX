# Test plan: NanoEX Web

Version 1.0 · 27 Oct 2026 · Format based on IEEE 829

## 1. Objectives
Show that every "must" requirement in the [SRS](SRS.md) works, that money is never created or lost by mistake, and that security controls hold.

## 2. Scope
In scope: backend services and API, matching engine, strategies, backtester, arbitrage, risk, React UI components, Docker deployment.
Out of scope: real exchange connectivity (none exists), load beyond a classroom (about 50 concurrent users), browser compatibility beyond current Chrome/Firefox/Edge/Safari.

## 3. Test levels and tools

| Level | What | Tool | Where |
|---|---|---|---|
| Unit | Order book, matching, indicators, strategies, cost model, arbitrage detector, risk rules, position maths, backtest metrics, market provider | pytest | `backend/tests/unit/` |
| Integration | Full API through FastAPI's ASGI client with a fresh SQLite database per test and a fixed-price market | pytest + httpx | `backend/tests/integration/` |
| Component | React UI components and pages | Vitest + React Testing Library | `frontend/src/test/` |
| System | Full stack via docker compose with PostgreSQL | manual + scripted (curl, Playwright) | see §7 |
| Static | Lint and format | ruff, black, eslint, prettier, tsc | CI |

## 4. Environment
- Python 3.12, Node 20, PostgreSQL 16 (Docker) or SQLite (tests).
- Tests use a `StaticProvider` so prices are fixed and results are deterministic.
- Rate limits are lowered in tests to check the 429 path quickly.

## 5. Entry and exit criteria
**Entry:** code compiles, lint passes.
**Exit:** all test cases pass; backend line coverage ≥ 80%; no open defect of severity High or Critical.

## 6. Test cases

Status as of 27 Oct 2026: **all pass**. Backend: 147 tests, 88% line coverage (matching engine ~100%, arbitrage cost model and detector 100%). Frontend: 15 tests.

### 6.1 Authentication and users

| ID | Requirement | Test case | Steps / input | Expected result | Automated test | Result |
|---|---|---|---|---|---|---|
| TC-01 | FR-1.1 | Register and fetch profile | POST /auth/register, /auth/login, GET /users/me | 201, token issued, profile returned | `test_register_login_me` | Pass |
| TC-02 | FR-2.1 | New user gets ₹5 L | Register, GET /wallet | balance = 500000.00 | `test_new_user_gets_five_lakh_wallet` | Pass |
| TC-03 | FR-1.1 | Duplicate email | Register same email twice | 409 EMAIL_TAKEN | `test_duplicate_email` | Pass |
| TC-04 | FR-1.1 | Weak password / bad email | "short", "not-an-email" | 422 VALIDATION_ERROR | `test_weak_password_and_bad_email` | Pass |
| TC-05 | FR-1.2 | Wrong password | Valid email, wrong password | 401, generic message | `test_wrong_password` | Pass |
| TC-06 | FR-1.7 | Protected route without token | GET /users/me with no header | 401 | `test_protected_route_requires_token` | Pass |
| TC-07 | FR-1.3 | Refresh rotation and reuse | Refresh twice with the same old cookie | 2nd use → 401 and all sessions revoked | `test_refresh_rotates_and_detects_reuse` | Pass |
| TC-08 | FR-1.4 | Logout revokes refresh | Logout, then refresh | 401 | `test_logout_revokes_refresh` | Pass |
| TC-09 | FR-1.5 | Change password | Change, log in with old and new | Old fails, new works | `test_change_password` | Pass |
| TC-10 | FR-1.6 | Login rate limit | 6 logins in a minute | 6th → 429 | `test_login_rate_limited` | Pass |
| TC-11 | FR-1.5 | Update profile | PATCH /users/me | Name changed | `test_update_profile` | Pass |
| TC-12 | NFR-11 | Health and metrics | GET /health, /metrics | 200, database true | `test_health_and_metrics` | Pass |
| TC-13 | NFR-3 | Production rejects weak JWT secret | ENVIRONMENT=production, short secret | Startup fails | `test_production_requires_strong_jwt_secret` | Pass |

### 6.2 Wallet

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-14 | FR-2.2, 2.3 | Top up ₹1 L | Balance and capital_added +1 L; profit unchanged | `test_top_up_adds_capital_not_profit` | Pass |
| TC-15 | FR-2.2 | Top-up above ₹10 L, or a negative amount | 422 TOPUP_LIMIT / VALIDATION_ERROR | `test_top_up_limits` | Pass |
| TC-16 | FR-2.4 | Reset while holding a position | 409; allowed once flat | `test_reset_requires_flat_portfolio` | Pass |

### 6.3 Order book and matching

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-17 | FR-4.4 | Non-crossing limit order | Rests in book | `test_limit_order_rests_when_not_crossing` | Pass |
| TC-18 | FR-4.2 | Best price fills first | Lower ask fills before higher | `test_price_priority_best_price_fills_first` | Pass |
| TC-19 | FR-4.2 | Same price, earlier order first | FIFO at a level | `test_time_priority_at_same_price` | Pass |
| TC-20 | FR-4.4 | Partial fill then rest | Remainder rests | `test_partial_fill_then_rest` | Pass |
| TC-21 | FR-4.2 | Trade price = resting price | Aggressor gets price improvement | `test_trade_executes_at_resting_price` | Pass |
| TC-22 | FR-4.3 | Market order remainder | Unfilled part cancelled (IOC) | `test_market_order_remainder_is_dropped` | Pass |
| TC-23 | FR-4.3 | Market order on empty book | No fills, cancelled | `test_market_order_on_empty_book` | Pass |
| TC-24 | FR-4.5 | Cancel removes order and empty level | Level gone from depth | `test_cancel_removes_order_and_level` | Pass |
| TC-25 | FR-4.6 | Self-trade prevention | Own resting order cancelled, no trade | `test_self_trade_prevention_cancels_resting` | Pass |
| TC-26 | FR-3.5 | Depth aggregation | Qty and order count per level | `test_depth_aggregates_levels` | Pass |
| TC-27 | FR-7.2 | VWAP sweep across levels | Correct average and fillable qty | `test_sweep_vwap_walks_levels` | Pass |
| TC-28 | — | Invalid input to the book | qty ≤ 0, limit without price, duplicate id rejected | `test_invalid_quantity`, `test_limit_needs_price`, `test_duplicate_order_id_rejected` | Pass |
| TC-29 | FR-4.4 | Resting user order fills when market moves | Liquidity maker crosses it | `test_resting_user_order_fills_when_market_moves` | Pass |

### 6.4 Orders, positions and P&L (API)

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-30 | FR-4.1 | Market buy | FILLED, position opened, cash reduced by value + charges | `test_market_buy_fills_and_creates_position` | Pass |
| TC-31 | FR-9.2 | Buy then sell | Realised P&L and fees recorded | `test_round_trip_realizes_pnl_and_fees` | Pass |
| TC-32 | FR-2.6, 4.5 | Limit rests then cancel | Funds blocked, then released | `test_limit_order_rests_then_cancel_releases_funds` | Pass |
| TC-33 | FR-4.4 | Resting limit fills later | Status FILLED after price move | `test_resting_limit_fills_when_market_moves` | Pass |
| TC-34 | FR-8.4 | Risk rejection saved | Order REJECTED with reason | `test_risk_rejection_is_recorded` | Pass |
| TC-35 | FR-8.1 | Insufficient funds | Rejected | `test_insufficient_funds` | Pass |
| TC-36 | FR-4.7 | Validation | Limit without price, off-tick price, price far from market → 422; unknown symbol → 404 | `test_validation_errors` | Pass |
| TC-37 | FR-8.3 | Kill switch | Blocks new orders, cancels open ones | `test_kill_switch_blocks_and_cancels` | Pass |
| TC-38 | FR-9.3 | CSV export | text/csv with header and rows | `test_trades_csv_export` | Pass |
| TC-39 | FR-9.2 | Profit dashboard | Totals match trades | `test_profit_dashboard` | Pass |
| TC-40 | FR-9.1 | Position maths | Averaging, partial close, flip, short cover | `test_position_math.py` (6 tests) | Pass |
| TC-41 | FR-9.1 | Buy NSE + sell BSE nets flat | Quantity 0, P&L realised | `test_arbitrage_buy_one_exchange_sell_other_nets_flat` | Pass |

### 6.5 Risk rules

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-42 | FR-8.1 | Order within limits | Passes all 8 rules | `test_passes_when_within_limits` | Pass |
| TC-43 | FR-8.1 | Each rule rejects on breach | Correct rule named in reason | `test_each_rule_rejects` | Pass |
| TC-44 | FR-8.5 | Short sale needs 20% margin | Rejected without margin | `test_short_sale_needs_margin` | Pass |
| TC-45 | FR-8.1 | Exits allowed after daily loss hit | Closing order passes | `test_exits_allowed_after_daily_loss` | Pass |

### 6.6 Strategies and backtesting

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-46 | FR-5.1 | Factory lists nine strategies | 9 types with schemas | `test_factory_lists_all_nine` | Pass |
| TC-47 | FR-5.3 | Bad params | Out of range, unknown, fast ≥ slow rejected | `test_param_out_of_range_and_unknown_param`, `test_cross_param_validation` | Pass |
| TC-48 | FR-5.1 | Each strategy signals correctly on crafted prices | BUY/SELL at the expected bar | 9 tests in `test_strategies.py` | Pass |
| TC-49 | FR-5.4 | SL / TP / trailing exits | Exit at the right price | `test_position_tracker_stop_loss_take_profit_trailing` | Pass |
| TC-50 | FR-5.2 | Bot trades on signal via API | Order with source STRATEGY and reason | `test_bot_trades_on_signal` | Pass |
| TC-51 | FR-6.2 | Backtest pays all charges | costs > 0 for every trade | `test_runner_produces_metrics_and_costs` | Pass |
| TC-52 | FR-6.4 | Same seed, same result | Identical metrics | `test_runner_is_deterministic`, `test_backtest_endpoint_is_reproducible` | Pass |
| TC-53 | FR-6.3 | Indicators | SMA, EMA, RSI, MACD, Bollinger, Z-score known values | `test_indicators.py` (13 tests) | Pass |

### 6.7 Arbitrage

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-54 | FR-6.2 | Buy leg pays stamp duty, no STT; sell leg pays STT | Charges match schedule | `test_buy_leg_has_stamp_no_stt`, `test_sell_leg_has_stt_no_stamp` | Pass |
| TC-55 | FR-6.2 | Brokerage cap | min(₹20, 0.03%) | `test_brokerage_cap_on_small_orders` | Pass |
| TC-56 | FR-7.2 | Zero spread | No opportunity | `test_zero_spread_is_not_an_opportunity` | Pass |
| TC-57 | FR-7.2 | Spread smaller than costs | Not actionable | `test_spread_smaller_than_costs` | Pass |
| TC-58 | FR-7.3 | Profitable spread | Buy on cheaper, sell on dearer | `test_profitable_opportunity_buys_cheap_sells_dear` | Pass |
| TC-59 | FR-7.3 | BSE cheaper than NSE | Direction reversed | `test_reverse_direction_when_bse_cheaper` | Pass |
| TC-60 | FR-7.2 | Thin book | Flagged low liquidity | `test_insufficient_liquidity_flags_opportunity` | Pass |
| TC-61 | FR-7.3 | Manual execution | Two FILLED legs, status COMPLETED, net P&L from fills | `test_manual_execution_two_legs_completed` | Pass |
| TC-62 | FR-7.6 | One leg fails | Filled leg flattened, status HEDGED | `test_failed_leg_is_flattened` | Pass |
| TC-63 | FR-7.6 | Both legs fail | Status FAILED, no position | `test_both_legs_fail` | Pass |
| TC-64 | FR-7.4 | Auto mode above threshold | Executes once, then cooldown | `test_auto_mode_executes_above_threshold` | Pass |
| TC-65 | FR-8.3 | Auto mode with kill switch on | Nothing executes | `test_auto_mode_respects_kill_switch` | Pass |
| TC-66 | FR-7.1 | Spread board | 10 symbols with NSE, BSE, diff | `test_spread_board_and_live_opportunities` | Pass |

### 6.8 Admin

| ID | Req | Test case | Expected | Automated test | Result |
|---|---|---|---|---|---|
| TC-67 | FR-1.7 | Non-admin hits admin route | 403 | `test_non_admin_forbidden` | Pass |
| TC-68 | FR-10.1, 10.2 | Admin lists, disables user, adjusts wallet | Disabled user can't log in; ledger entry ADMIN_ADJUST | `test_admin_can_list_disable_and_adjust` | Pass |
| TC-69 | FR-10.3 | Metrics and audit log | Entries present | `test_admin_metrics_and_audit` | Pass |

### 6.9 Frontend (Vitest + RTL)

| ID | Test case | Expected | File | Result |
|---|---|---|---|---|
| TC-70 | Indian number formatting | ₹5,00,000 grouping, ₹5.00 L, ₹1.20 Cr | `format.test.ts` | Pass |
| TC-71 | UTC handling for timezone-less timestamps | Parsed as UTC | `format.test.ts` | Pass |
| TC-72 | Password rule | Short/weak rejected | `components.test.tsx` | Pass |
| TC-73 | Table and empty state | Rows rendered; empty message | `components.test.tsx` | Pass |
| TC-74 | Paper badge and disclaimer render | Text visible | `components.test.tsx` | Pass |
| TC-75 | Depth table | Bids and asks with formatted prices | `components.test.tsx` | Pass |
| TC-76 | Login page | Disclaimer shown; success stores session; failure shows API message | `login.test.tsx` | Pass |

## 7. System test (manual, run on 27 Oct 2026)

Environment: `docker compose up --build` (PostgreSQL 16, backend, nginx frontend).

| ID | Scenario | Result |
|---|---|---|
| ST-01 | Stack starts; `/health` reports database and market stream OK | Pass |
| ST-02 | Alembic migration creates the same schema as the models (compared table by table) | Pass |
| ST-03 | Admin from env can log in; Admin menu visible | Pass |
| ST-04 | Place 5 market orders; dashboard, portfolio and history update live | Pass |
| ST-05 | Enable auto arbitrage (min ₹1, 50 shares); trades appear with COMPLETED/HEDGED status | Pass |
| ST-06 | Start a Momentum bot on ITC | Pass |
| ST-07 | Run an EMA backtest on RELIANCE; metrics and equity curve shown | Pass |
| ST-08 | Every page loads with no browser console errors (Playwright) | Pass |

## 8. Performance check

| Metric | Target | Measured (laptop, SQLite) |
|---|---|---|
| Average order latency (risk + match + persist) | < 50 ms | ~19 ms |
| Market tick interval | 500 ms | 500 ms |
| WebSocket update delay | < 1 tick | < 1 tick |

## 9. Defect log (found during development)

| ID | Defect | Severity | Fix |
|---|---|---|---|
| D-01 | Arbitrage sell leg filled while buy leg was rejected for funds, leaving a naked short | High | Executor checks funds for the buy leg before sending any leg |
| D-02 | Portfolio sum returned int, breaking decimal rounding with no positions | Medium | Sum with a Decimal zero start value |
| D-03 | Bot runner crashed on shutdown when started without background tasks | Low | Guarded the queue unsubscribe |
| D-04 | SQLite drops timezone, so browser showed times 5.5 h off | Medium | Frontend treats timezone-less timestamps as UTC |
| D-05 | Example admin email `admin@nanoex.local` rejected by the email validator (reserved domain) | Low | Changed to `admin@nanoex.in` |

## 10. How to run

```bash
# backend
cd backend && pytest --cov=app
# frontend
cd frontend && npm test
```
