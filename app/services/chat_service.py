import json
from app.core.redis import redis_client
from app.repositories.chat_repository import ChatRepository


class ChatService:
    def __init__(self, db):
        self.repo = ChatRepository(db)

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
        """Salva no Redis (curto prazo) e DB (longo prazo)."""
        msg = {"role": role, "content": content}

        # Redis: Mantém apenas as últimas 20 mensagens para o LLM não estourar tokens
        await redis_client.lpush(f"chat:{session_id}", json.dumps(msg))
        await redis_client.ltrim(f"chat:{session_id}", 0, 19)
        await redis_client.expire(
            f"chat:{session_id}", 3600
        )  # Expira em 1h de inatividade

        # DB: Persistência permanente
        await self.repo.add_message(session_id, role, content)

    async def create_session(self, user_id: str, title: str):
        """Cria uma nova sessão."""
        await redis_client.hset(f"chat:{user_id}", "title", title)
        await redis_client.expire(f"chat:{user_id}", 3600)
        session = await self.repo.create_session(user_id, title)
        return session

    async def clear_session(self, session_id: str):
        """Limpa histórico."""
        await redis_client.delete(f"chat:{session_id}")
        await self.repo.delete_session(session_id)
