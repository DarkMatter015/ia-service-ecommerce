from typing import Generic, TypeVar, Type, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get(self, id: Any) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()

    async def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, obj_in: ModelType) -> ModelType:
        self.db.add(obj_in)
        await self.db.commit()
        await self.db.refresh(obj_in)
        return obj_in

    async def update(self, db_obj: ModelType, obj_in: Any) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> ModelType:
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        obj = result.scalars().first()
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
        return obj

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar()

    async def order_by(self, field: str, order: str = "asc") -> List[ModelType]:
        query = select(self.model).order_by(getattr(self.model, field))
        if order == "desc":
            query = select(self.model).order_by(getattr(self.model, field).desc())

        result = await self.db.execute(query)
        return result.scalars().all()
