from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.events import publish_wallet
from app.core.responses import ok
from app.models.user import User
from app.repositories.wallet_repo import WalletTransactionRepository
from app.schemas.wallet import TopUpRequest, WalletOut, WalletTxnOut
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _wallet_json(wallet) -> dict:
    return WalletOut.model_validate(wallet).model_dump(mode="json")


@router.get("")
async def get_wallet(user: User = CurrentUser, session: AsyncSession = SessionDep):
    return ok(_wallet_json(await WalletService(session).get(user.id)))


@router.get("/transactions")
async def transactions(
    type: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    wallet = await WalletService(session).get(user.id)
    repo = WalletTransactionRepository(session)
    items, total = await repo.page(repo.for_wallet(wallet.id, type), page, size)
    data = [WalletTxnOut.model_validate(t).model_dump(mode="json") for t in items]
    return ok(data, meta={"total": total, "page": page, "size": size})


@router.post("/topup")
async def top_up(body: TopUpRequest, user: User = CurrentUser, session: AsyncSession = SessionDep):
    wallet = await WalletService(session).top_up(user.id, body.amount, body.note)
    data = _wallet_json(wallet)
    publish_wallet(user.id, data)
    return ok(data)


@router.post("/reset")
async def reset(user: User = CurrentUser, session: AsyncSession = SessionDep):
    wallet = await WalletService(session).reset(user.id)
    data = _wallet_json(wallet)
    publish_wallet(user.id, data)
    return ok(data)
