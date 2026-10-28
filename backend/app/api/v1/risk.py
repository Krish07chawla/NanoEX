from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, get_container
from app.core.responses import ok
from app.models.user import User
from app.schemas.risk import KillSwitchRequest, RiskSettingsOut, RiskSettingsUpdate
from app.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
async def get_risk(user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok(RiskSettingsOut.model_validate(await RiskService(session, c).get(user.id)).model_dump(mode="json"))


@router.put("")
async def update_risk(
    body: RiskSettingsUpdate, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    s = await RiskService(session, c).update(user.id, body)
    return ok(RiskSettingsOut.model_validate(s).model_dump(mode="json"))


@router.post("/kill-switch")
async def kill_switch(
    body: KillSwitchRequest, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(await RiskService(session, c).kill_switch(user, body.enabled, body.cancel_open_orders))
