from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep
from app.core.responses import ok
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(user: User = CurrentUser):
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.patch("/me")
async def update_me(body: UserUpdate, user: User = CurrentUser, session: AsyncSession = SessionDep):
    if body.full_name:
        user.full_name = body.full_name
    await session.flush()
    return ok(UserOut.model_validate(user).model_dump(mode="json"))
