from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, SessionDep, get_container
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.responses import ok
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.schemas.user import AdminUserUpdate, UserOut
from app.schemas.wallet import AdminWalletAdjust, WalletOut
from app.services.admin_service import AdminService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def users(
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: User = AdminUser,
    session: AsyncSession = SessionDep,
    c=Depends(get_container),
):
    data, total = await AdminService(session, c).list_users((page - 1) * size, size)
    return ok(data, meta={"total": total, "page": page, "size": size})


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    admin: User = AdminUser,
    session: AsyncSession = SessionDep,
    c=Depends(get_container),
):
    user = await AdminService(session, c).update_user(admin, user_id, body)
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/users/{user_id}/wallet-adjust")
async def adjust_wallet(
    user_id: str, body: AdminWalletAdjust, admin: User = AdminUser, session: AsyncSession = SessionDep
):
    wallet = await WalletService(session).admin_adjust(admin.id, user_id, body.amount, body.note)
    return ok(WalletOut.model_validate(wallet).model_dump(mode="json"))


@router.get("/metrics")
async def system_metrics(_: User = AdminUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok(await AdminService(session, c).system_metrics())


@router.get("/audit-logs")
async def audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: User = AdminUser,
    session: AsyncSession = SessionDep,
):
    repo = AuditLogRepository(session)
    items, total = await repo.page(repo.query(user_id, action), page, size)
    data = [
        {
            "id": a.id,
            "user_id": a.user_id,
            "action": a.action,
            "entity": a.entity,
            "entity_id": a.entity_id,
            "ip_address": a.ip_address,
            "details": a.details,
            "created_at": a.created_at.isoformat(),
        }
        for a in items
    ]
    return ok(data, meta={"total": total, "page": page, "size": size})
