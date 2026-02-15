from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime
from sqlalchemy.dialects.postgresql import UUID, BigInteger
import uuid
import timezone


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    # Usamos UUID nativo para performance e segurança
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Alinhado com o BIGINT do Java/Postgres
    user_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(255), nullable=True)

    # timezone=True garante compatibilidade com TIMESTAMPTZ
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    # BIGSERIAL no Postgres mapeia para BigInteger no SQLAlchemy
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )

    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("ChatSession", back_populates="messages")
