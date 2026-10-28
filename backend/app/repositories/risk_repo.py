from sqlalchemy import select

from app.models.risk_settings import RiskSettings
from app.repositories.base import BaseRepository


class RiskSettingsRepository(BaseRepository[RiskSettings]):
    model = RiskSettings

    async def get_by_user(self, user_id: str) -> RiskSettings | None:
        result = await self.session.execute(select(RiskSettings).where(RiskSettings.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: str) -> RiskSettings:
        settings = await self.get_by_user(user_id)
        if settings is None:
            settings = await self.add(RiskSettings(user_id=user_id))
        return settings

    async def users_with_auto_arb(self) -> list[str]:
        result = await self.session.execute(
            select(RiskSettings.user_id).where(
                RiskSettings.arb_auto_enabled.is_(True), RiskSettings.kill_switch.is_(False)
            )
        )
        return list(result.scalars().all())
