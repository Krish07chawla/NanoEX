"""Domain constants and enums. No magic numbers elsewhere in the code."""

from decimal import Decimal
from enum import StrEnum


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderSource(StrEnum):
    MANUAL = "MANUAL"
    STRATEGY = "STRATEGY"
    ARBITRAGE = "ARBITRAGE"


class WalletTxnType(StrEnum):
    INITIAL = "INITIAL"
    TOPUP = "TOPUP"
    RESET = "RESET"
    TRADE_DEBIT = "TRADE_DEBIT"
    TRADE_CREDIT = "TRADE_CREDIT"
    FEE = "FEE"
    ADMIN_ADJUST = "ADMIN_ADJUST"


class ArbMode(StrEnum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class ArbStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    HEDGED = "HEDGED"  # one leg failed, the filled leg was flattened
    FAILED = "FAILED"  # neither leg filled


class AuditAction(StrEnum):
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    ORDER = "ORDER"
    ORDER_CANCEL = "ORDER_CANCEL"
    TRADE = "TRADE"
    WALLET_TOPUP = "WALLET_TOPUP"
    WALLET_RESET = "WALLET_RESET"
    RISK_CHANGE = "RISK_CHANGE"
    KILL_SWITCH = "KILL_SWITCH"
    ARBITRAGE = "ARBITRAGE"
    ADMIN_ACTION = "ADMIN_ACTION"


# --- Money / precision ---
PAISE = Decimal("0.01")
PRICE_PRECISION = Decimal("0.0001")
TICK_SIZE = Decimal("0.05")  # NSE/BSE equity tick size

# --- Pagination ---
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200

# --- Default risk settings (per user, editable) ---
DEFAULT_MAX_ORDER_QTY = 5_000
DEFAULT_MAX_ORDER_NOTIONAL = Decimal("500000")
DEFAULT_MAX_POSITION_VALUE = Decimal("1000000")
DEFAULT_DAILY_LOSS_LIMIT = Decimal("50000")
DEFAULT_DAILY_VOLUME_CAP = Decimal("5000000")
DEFAULT_MAX_OPEN_ORDERS = 50
DEFAULT_ARB_MIN_PROFIT = Decimal("50")
DEFAULT_ARB_QTY = 100

# --- Simulated universe: symbol -> (approx. reference price in INR, annual volatility) ---
SYMBOL_UNIVERSE: dict[str, tuple[float, float]] = {
    "RELIANCE": (2900.0, 0.22),
    "TCS": (4100.0, 0.20),
    "INFY": (1850.0, 0.24),
    "HDFCBANK": (1650.0, 0.20),
    "ICICIBANK": (1250.0, 0.22),
    "SBIN": (820.0, 0.28),
    "ITC": (470.0, 0.18),
    "LT": (3600.0, 0.24),
    "WIPRO": (560.0, 0.26),
    "AXISBANK": (1150.0, 0.25),
}
