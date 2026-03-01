"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session. Commits on success, rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
