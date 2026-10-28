from fastapi import APIRouter

from app.api.v1 import (
    admin,
    arbitrage,
    auth,
    dashboard,
    market,
    orders,
    portfolio,
    risk,
    strategies,
    system,
    users,
    wallet,
)

api_router = APIRouter()
for module in (auth, users, wallet, market, orders, strategies, arbitrage, portfolio, dashboard, risk, admin, system):
    api_router.include_router(module.router)
