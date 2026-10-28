"""Writes audit log entries for logins, trades, wallet and risk changes."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_repo import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.repo = AuditLogRepository(session)

    async def log(
        self,
        action: str,
        *,
        user_id: str | None = None,
        entity: str | None = None,
        entity_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.repo.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                ip_address=ip,
                user_agent=(user_agent or "")[:255] or None,
                details=details or {},
            )
        )
