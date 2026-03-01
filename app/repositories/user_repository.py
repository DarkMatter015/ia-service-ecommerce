from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_model import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def exists_by_user_id(self, user_id: int) -> bool:
        result = await self.db.execute(
            select(self.model).filter(self.model.id == user_id)
        )
        return result.scalars().first() is not None
