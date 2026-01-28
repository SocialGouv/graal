"""Service to persist OAuth authentication requests (state + PKCE)."""

import logging
import logging.config
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.database.models import OAuthAuthRequest

logging.config.fileConfig("logging.conf")


class OAuthStateService:
    """Persistence layer for OAuth state/PKCE verifier pairs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        logging.info("[OAuthStateService] Initialized")

    async def create_state(
        self,
        state: str,
        code_verifier: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OAuthAuthRequest:
        async with self._session_factory() as session:
            record = OAuthAuthRequest(
                id=uuid.uuid4(),
                state=state,
                code_verifier=code_verifier,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logging.info("[OAuthStateService] Stored OAuth state (ip=%s)", ip_address)
            return record

    async def consume_state(
        self, state: str, *, max_age_seconds: int
    ) -> OAuthAuthRequest | None:
        """Fetch and invalidate an OAuth state.

        Returns the most recent matching record if it exists and is still within
        ``max_age_seconds``. Returns ``None`` when the state is missing (e.g. it
        was never issued or already consumed) or when it exists but has expired
        and is consequently deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)

        async with self._session_factory() as session:
            result = await session.execute(
                select(OAuthAuthRequest)
                .where(OAuthAuthRequest.state == state)
                .order_by(OAuthAuthRequest.created_at.desc())
                .limit(1)
            )
            record: OAuthAuthRequest | None = result.scalar_one_or_none()

            if not record:
                logging.warning(
                    "[OAuthStateService] No state found for %s (maybe already used)",
                    state[:8],
                )
                return None

            if record.created_at < cutoff:
                logging.warning(
                    "[OAuthStateService] State %s expired (created_at=%s)",
                    state[:8],
                    record.created_at,
                )
                await session.delete(record)
                await session.commit()
                return None

            await session.delete(record)
            await session.commit()
            logging.info("[OAuthStateService] Consumed state %s", state[:8])
            return record


_oauth_state_service: Optional[OAuthStateService] = None


def get_oauth_state_service() -> OAuthStateService:
    global _oauth_state_service
    if _oauth_state_service is None:
        from graal.database.base import get_async_session_maker

        session_factory = get_async_session_maker()
        _oauth_state_service = OAuthStateService(session_factory)
    return _oauth_state_service
