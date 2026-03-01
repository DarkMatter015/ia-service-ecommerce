import json
import logging

from fastapi import HTTPException, status

from app.core.redis import redis_client
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository
from app.schemas.session_schema import SessionResponse

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db):
        self.repo = ChatRepository(db)
        self.userRepository = UserRepository(db)

    async def get_context(self, session_id: str, limit: int = 10):
        """Busca contexto rápido no Redis, se não houver, busca no DB."""
        # 1. Tentar Redis
        history = await redis_client.lrange(f"chat:{session_id}", 0, limit - 1)
        if history:
            return [json.loads(m) for m in history][::-1]

        # 2. Fallback DB (Se o Redis expirou)
        db_history = await self.repo.get_messages(session_id, limit)
        return [{"role": m.role, "content": m.content} for m in db_history]

    async def save_message(self, session_id: str, role: str, content: str):
        try:
            """Salva no Redis (curto prazo) e DB (longo prazo)."""
            logging.info(
                f"Salvando mensagem - Session: {session_id}, Role: {role}, Content: {content[:30]}..."
            )
            msg = {"role": role, "content": content}

            # Redis: Mantém apenas as últimas 20 mensagens para o LLM não estourar tokens
            await redis_client.lpush(f"chat:{session_id}", json.dumps(msg))
            await redis_client.ltrim(f"chat:{session_id}", 0, 19)
            await redis_client.expire(
                f"chat:{session_id}", 3600
            )  # Expira em 1h de inatividade

            # DB: Persistência permanente
            logging.info("Salvando mensagem no DB...")
            await self.repo.add_message(session_id, role, content)
        except Exception as e:
            logging.error("Erro ao salvar mensagem: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao salvar mensagem!",
            )

    async def save_context_only(self, session_id: str, role: str, content: str):
        try:
            """Salva no Redis (curto prazo) apenas, sem tocar no DB."""
            logging.info(
                f"Salvando contexto - Session: {session_id}, Role: {role}, Content: {content[:30]}..."
            )
            msg = {"role": role, "content": content}

            # Redis: Mantém apenas as últimas 20 mensagens para o LLM não estourar tokens
            await redis_client.lpush(f"chat:{session_id}", json.dumps(msg))
            await redis_client.ltrim(f"chat:{session_id}", 0, 19)
            await redis_client.expire(
                f"chat:{session_id}", 3600
            )  # Expira em 1h de inatividade

        except Exception as e:
            logging.error("Erro ao salvar contexto: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao salvar contexto!",
            )

    async def create_session(self, user_id: str, title: str) -> SessionResponse:
        """Cria nova sessão de chat."""
        exists = await self.userRepository.exists_by_user_id(int(user_id))
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado!"
            )

        """Cria uma nova sessão."""
        await redis_client.hset(f"chat:{user_id}", "title", title)
        await redis_client.expire(
            f"chat:{user_id}", 3600
        )  # Expira em 1h de inatividade
        session = await self.repo.create_session(int(user_id), title)
        return SessionResponse(
            id=str(session.id),
            user_id=session.user_id,
            title=session.title,
            created_at=str(session.created_at),
        )

    async def clear_session(self, session_id: str):
        """Limpa histórico."""
        await redis_client.delete(f"chat:{session_id}")
        await self.repo.delete_session(session_id)

    async def get_session(self, session_id: str) -> SessionResponse:
        """Busca sessão por ID."""
        session = await self.repo.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada!"
            )
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=str(session.created_at),
        )
