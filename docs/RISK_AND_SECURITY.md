# Risk analysis and security checklist: NanoEX Web

## 1. Project risk register

Likelihood (L) and impact (I) are scored 1 (low) to 3 (high). Exposure = L × I.

| ID | Risk | Category | L | I | Exp. | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | Users mistake the simulator for real trading or treat it as advice | Legal / ethical | 2 | 3 | 6 | "PAPER TRADING · SIMULATION" badge on every screen, disclaimer on login and footer, honest arbitrage note, no broker integration in code | PO | Closed |
| R-02 | Matching-engine bug creates or destroys virtual money | Technical | 2 | 3 | 6 | Decimal money everywhere, append-only wallet ledger, ~100% test coverage of the order book | Dev | Closed |
| R-03 | Arbitrage leaves a naked position when one leg fails | Technical | 3 | 2 | 6 | Funds pre-check, leg flattening, HEDGED status, tests for leg failure | Dev | Closed |
| R-04 | Stolen JWT or refresh token | Security | 2 | 3 | 6 | Short access token, httpOnly refresh cookie, rotation with reuse detection | Dev | Closed |
| R-05 | Brute-force login | Security | 3 | 2 | 6 | Rate limit 5/min per IP, generic error message, constant-time check, audit of failed logins | Dev | Closed |
| R-06 | Secrets committed to git | Security | 2 | 3 | 6 | `.env` ignored, `.env.example` only, pre-commit `detect-private-key`, production refuses the dev JWT secret | Dev | Closed |
| R-07 | Single process cannot scale past one machine | Architecture | 2 | 1 | 2 | Acceptable for a classroom; future work: move order books to a separate engine service with Redis pub/sub | Arch | Accepted |
| R-08 | SQLite locking under concurrent writes | Technical | 2 | 2 | 4 | WAL mode, short transactions; PostgreSQL in Docker | Dev | Closed |
| R-09 | yfinance unavailable or rate-limited | External | 3 | 1 | 3 | Synthetic provider is the default; yfinance is optional | Dev | Accepted |
| R-10 | Scope creep (F&O, more strategies) delays delivery | Schedule | 2 | 2 | 4 | Product Owner owns backlog; extras listed as future work | PO | Open (monitor) |
| R-11 | Team member unavailable near a deadline | People | 2 | 2 | 4 | Pairing on engine and arbitrage; docs kept current | SM | Open (monitor) |
| R-12 | Unrealistic results mislead learners | Educational | 2 | 2 | 4 | Real Indian charges in backtests and arbitrage, slippage, latency and leg-failure simulation | Dev | Closed |

## 2. OWASP Top 10 (2021) checklist

| # | Category | Controls in NanoEX Web | Where | Status |
|---|---|---|---|---|
| A01 | Broken access control | Every route depends on `get_current_user`; admin routes on `require_admin`; every query filters by the caller's `user_id` (users can't read others' orders by id); disabled users rejected; WebSocket user channel checks the token | `app/api/deps.py`, repositories | ✅ |
| A02 | Cryptographic failures | bcrypt (12 rounds) for passwords; JWT HS256 with a secret from env (≥ 32 chars enforced in production); refresh cookie `HttpOnly`, `SameSite=Strict`, `Secure` when `COOKIE_SECURE=true`; no secrets in code | `app/core/security.py`, `config.py` | ✅ |
| A03 | Injection | SQLAlchemy ORM with bound parameters only; Pydantic validation of every request body and query; symbols checked against a whitelist; React escapes output (no `dangerouslySetInnerHTML`) | schemas, repositories | ✅ |
| A04 | Insecure design | Threat-aware design: pre-trade risk chain, kill switch, wallet ledger, top-up limits, reset only when flat, no real-broker code path | engine, services | ✅ |
| A05 | Security misconfiguration | CORS restricted to configured origins; security headers (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`); debug off by default; generic 500 handler (no stack traces to clients); containers run as non-root | `app/main.py`, Dockerfiles, nginx.conf | ✅ |
| A06 | Vulnerable and outdated components | Pinned minimum versions; CI installs fresh; recommend `pip-audit` and `npm audit` in CI (future work) | requirements, package.json | ⚠️ Partly |
| A07 | Identification and authentication failures | Password policy (8+, letter + number); rate-limited login/register; constant-time check with a dummy hash to stop user enumeration; refresh rotation and reuse detection; logout revokes; password change revokes all sessions | `auth_service.py` | ✅ |
| A08 | Software and data integrity failures | Lock files committed (`package-lock.json`); CI on every push; append-only wallet ledger and audit log | CI, models | ✅ |
| A09 | Security logging and monitoring failures | Structured JSON logs with request id; audit log for login, failed login, logout, register, password change, orders, top-ups, resets, kill switch and admin actions; admin audit-log viewer | `app/core/logging.py`, `audit_service.py` | ✅ |
| A10 | Server-side request forgery | The server makes no outbound requests based on user input; yfinance symbols come from a fixed whitelist | market providers | ✅ |

### Known limitations (accepted for an educational project)

| Item | Why accepted | Fix if deployed publicly |
|---|---|---|
| WebSocket user channel takes the access token as a query parameter | Browsers can't set headers on WebSocket connections; the token lives only 15 minutes | Use a one-time WS ticket from a REST call, or the `Sec-WebSocket-Protocol` header |
| `/health` and `/metrics` are public | Needed by Docker health checks; they expose no user data | Restrict `/metrics` to the internal network in nginx |
| Rate limiting is in-memory | Single process | Use Redis-backed limits when running several replicas |
| No TLS inside docker compose | Local classroom use | Terminate TLS in front of nginx and set `COOKIE_SECURE=true` |
| No dependency scanning in CI | Time | Add `pip-audit` and `npm audit --audit-level=high` jobs |

## 3. Data protection
- Stored personal data: email, full name, password hash, IP address and user agent in audit logs. No payment or KYC data.
- Users can change their name and password; admins can disable accounts.
- No real financial data is processed; all balances are virtual.
