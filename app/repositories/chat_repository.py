from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_model import ChatMessage, ChatSession
from app.repositories.base_repository import BaseRepository


class ChatRepository(BaseRepository[ChatSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatSession)

    async def get_messages(self, session_id: str, limit: int = 10) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .limit(limit)
            .all()
        )

    async def add_message(
        self, session_id: str, role: str, content: str
    ) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def delete_session(self, session_id: str) -> None:
        self.db.query(ChatSession).filter(ChatSession.id == session_id).delete()
        await self.db.commit()

    async def get_sessions(self, user_id: int) -> list[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.user_id == user_id).all()

    async def get_session(self, session_id: str) -> ChatSession | None:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    async def create_session(self, user_id: int, title: str) -> ChatSession:
        try:
            session = ChatSession(user_id=user_id, title=title)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            return session
        except Exception as e:
            await self.db.rollback()
            raise e

    async def exist_session(self, session_id: str) -> bool:
        result = await self.db.execute(
            select(self.model).filter_by(id=session_id)
        )
        return result.scalars().first() is not None