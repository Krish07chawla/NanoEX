"""Import every model so Base.metadata knows all tables (used by Alembic + create_all)."""

from app.models.arbitrage import ArbitrageOpportunity, ArbitrageTrade
from app.models.audit_log import AuditLog
from app.models.backtest_result import BacktestResult
from app.models.order import Order
from app.models.position import Position
from app.models.risk_settings import RiskSettings
from app.models.strategy_config import StrategyConfig
from app.models.trade import Trade
from app.models.user import RefreshToken, User
from app.models.wallet import Wallet, WalletTransaction

__all__ = [
    "ArbitrageOpportunity",
    "ArbitrageTrade",
    "AuditLog",
    "BacktestResult",
    "Order",
    "Position",
    "RefreshToken",
    "RiskSettings",
    "StrategyConfig",
    "Trade",
    "User",
    "Wallet",
    "WalletTransaction",
]
