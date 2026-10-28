from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, get_container
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.exceptions import DomainError
from app.core.responses import ok
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.schemas.order import OrderOut, PlaceOrderRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _out(order) -> dict:
    return OrderOut.model_validate(order).model_dump(mode="json")


@router.post("", status_code=201)
async def place_order(
    body: PlaceOrderRequest, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    try:
        order = await OrderService(session, c).place(user, body)
    except DomainError:
        await session.commit()  # keep the REJECTED order row for the order history
        raise
    return ok(_out(order))


@router.get("")
async def list_orders(
    status: str | None = None,
    symbol: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    repo = OrderRepository(session)
    items, total = await repo.page(repo.for_user(user.id, status, symbol.upper() if symbol else None), page, size)
    return ok([_out(o) for o in items], meta={"total": total, "page": page, "size": size})


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(_out(await OrderService(session, c).cancel(user, order_id)))
