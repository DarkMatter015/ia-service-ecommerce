from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)  # UUID gerado no Front ou Back
    user_id = Column(Integer, index=True)
    title = Column(String, nullable=True)  # Ex: "Dúvida sobre Guitarra"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)  # 'user' ou 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")
