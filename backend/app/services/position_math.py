"""Pure position accounting (average-cost method). Supports longs and shorts."""

from decimal import Decimal

from app.core.constants import Side


def apply_fill(qty: int, avg: Decimal, side: Side, price: Decimal, fill_qty: int) -> tuple[int, Decimal, Decimal]:
    """Return (new_qty, new_avg_price, realized_pnl) after a fill."""
    signed = fill_qty if side is Side.BUY else -fill_qty
    if qty == 0 or (qty > 0) == (signed > 0):
        new_qty = qty + signed
        new_avg = (avg * abs(qty) + price * fill_qty) / abs(new_qty)
        return new_qty, new_avg, Decimal("0")
    closing = min(fill_qty, abs(qty))
    direction = 1 if qty > 0 else -1
    realized = (price - avg) * closing * direction
    new_qty = qty + signed
    if new_qty == 0:
        new_avg = Decimal("0")
    elif (new_qty > 0) != (qty > 0):  # flipped from long to short or vice versa
        new_avg = price
    else:
        new_avg = avg
    return new_qty, new_avg, realized
