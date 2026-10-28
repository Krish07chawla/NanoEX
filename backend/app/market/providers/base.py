"""MarketDataProvider interface (Adapter target). Every data source adapts to this."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    """Top-of-book snapshot for one symbol on one exchange."""

    symbol: str
    exchange: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: int
    timestamp: float  # unix seconds

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / 2

    def to_dict(self) -> dict:
        d = asdict(self)
        for key in ("bid", "ask", "last"):
            d[key] = float(d[key])
        return d


class MarketDataProvider(ABC):
    """A source of NSE/BSE quotes. Implementations: SyntheticProvider, YFinanceProvider."""

    name: str = "base"
    is_realtime: bool = False

    @abstractmethod
    def symbols(self) -> list[str]:
        """Symbols this provider can quote."""

    @abstractmethod
    async def next_quotes(self) -> list[Quote]:
        """Return the latest quote for every symbol on both exchanges."""
