from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api.deps import get_db
from app.services.agent_service import AgentService
import logging

router = APIRouter()

security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/message", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    token_auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        full_token = f"Bearer {token_auth.credentials}" if token_auth else None
        service = AgentService(db, user_token=full_token)
        answer = await service.handle_request(request.message)
        return ChatResponse(response=answer)
    except Exception as e:
        logger.error("🔥 ERRO CRÍTICO NO CHAT", exc_info=True)

        fallback_message = (
            "Eita, Lenda! 🎸 Deu uma microfonia nervosa aqui no meu sistema e "
            "perdi a conexão com o estúdio. 🔌"
            "Pode repetir a pergunta, por favor? Se continuar falhando, "
            "tente novamente em alguns minutos enquanto eu afino as cordas!"
        )

        return ChatResponse(response=fallback_message)
