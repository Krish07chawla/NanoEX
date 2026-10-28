"""Shared fixtures. Env vars are set before any app module reads settings."""

import os

os.environ.update(
    {
        "BCRYPT_ROUNDS": "4",
        "RATE_LIMIT_AUTH": "10/minute",
        "AUTO_CREATE_TABLES": "true",
        "SIM_SEED": "7",
        "ARB_MIN_LATENCY_MS": "1",
        "ARB_MAX_LATENCY_MS": "2",
        "ARB_LEG_FAILURE_PROB": "0",
        "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-123",
    }
)

import time  # noqa: E402
from decimal import Decimal  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.constants import Exchange  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.session import init_engine  # noqa: E402
from app.market.providers.base import MarketDataProvider, Quote  # noqa: E402

D = Decimal
PASSWORD = "secret123"


class StaticProvider(MarketDataProvider):
    """Deterministic quotes that tests can change: prices[(symbol, exchange)] = last."""

    name = "static"

    def __init__(self, prices: dict[tuple[str, str], Decimal] | None = None, half_spread: Decimal = D("0.05")):
        self.prices = prices or {
            ("RELIANCE", "NSE"): D("2900.00"),
            ("RELIANCE", "BSE"): D("2900.00"),
            ("TCS", "NSE"): D("4100.00"),
            ("TCS", "BSE"): D("4100.00"),
            ("SBIN", "NSE"): D("820.00"),
            ("SBIN", "BSE"): D("820.00"),
        }
        self.half_spread = half_spread

    def symbols(self) -> list[str]:
        return sorted({s for s, _ in self.prices})

    async def next_quotes(self) -> list[Quote]:
        now = time.time()
        return [
            Quote(s, e, p - self.half_spread, p + self.half_spread, p, 1000, now) for (s, e), p in self.prices.items()
        ]

    def set(self, symbol: str, nse: str, bse: str) -> None:
        self.prices[(symbol, Exchange.NSE.value)] = D(nse)
        self.prices[(symbol, Exchange.BSE.value)] = D(bse)


@pytest.fixture
def provider() -> StaticProvider:
    return StaticProvider()


@pytest.fixture
async def app(tmp_path, provider):
    from app.main import create_app

    init_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    limiter.reset()
    application = create_app(get_settings(), provider=provider, background=False)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
def container(app):
    return app.state.container


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_and_login(client: httpx.AsyncClient, email: str = "trader@example.com") -> dict:
    r = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Test User"}
    )
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.fixture
async def auth(client) -> dict:
    return await register_and_login(client)
