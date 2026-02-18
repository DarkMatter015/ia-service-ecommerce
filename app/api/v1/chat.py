from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
import logging

router = APIRouter()

security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


@router.post("/message", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    token_auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        full_token = f"Bearer {token_auth.credentials}" if token_auth else None
        service = AgentService(db, user_token=full_token)
        answer = await service.handle_request(request.message, request.session_id)
        return ChatResponse(response=answer)
    except Exception:
        logger.error("🔥 ERRO CRÍTICO NO CHAT", exc_info=True)

        fallback_message = (
            "Eita, Lenda! 🎸 Deu uma microfonia nervosa aqui no meu sistema e "
            "perdi a conexão com o estúdio. 🔌"
            "Pode repetir a pergunta, por favor? Se continuar falhando, "
            "tente novamente em alguns minutos enquanto eu afino as cordas!"
        )

        return ChatResponse(response=fallback_message)

@router.post("/session")
async def chat_endpoint_post(
    db: AsyncSession = Depends(get_db),
    token_auth: HTTPAuthorizationCredentials = Depends(security),
    user_id: str = None,
    title: str = None,
):
    try:
        full_token = f"Bearer {token_auth.credentials}" if token_auth else None
        if not full_token:
            return ChatResponse(response="Token não fornecido!")

        service = ChatService(db)
        session = await service.create_session(user_id, title)
        return ChatResponse(response=session)
    except Exception:
        logger.error("🔥 ERRO CRÍTICO AO CRIAR SESSÃO", exc_info=True)
        return ChatResponse(response="Erro ao criar sessão!")


@router.delete("/session/{session_id}")
async def chat_endpoint_delete(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    token_auth: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        full_token = f"Bearer {token_auth.credentials}" if token_auth else None
        if not full_token:
            return ChatResponse(response="Token não fornecido!")

        service = ChatService(db)
        await service.clear_session(session_id)
        return ChatResponse(response="Sessão limpa com sucesso!")
    except Exception:
        logger.error("🔥 ERRO CRÍTICO AO LIMPAR SESSÃO", exc_info=True)
        return ChatResponse(response="Erro ao limpar sessão!")