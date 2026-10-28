"""Time helpers. The trading day is the IST calendar day."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def start_of_trading_day() -> datetime:
    now_ist = datetime.now(IST)
    return now_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
