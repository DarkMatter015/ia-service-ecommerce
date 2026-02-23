import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService

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
        return ChatResponse(response=answer.response, session_id=answer.session_id)
    except HTTPException:
        raise
    except Exception:
        logger.error("🔥 ERRO CRÍTICO NO CHAT", exc_info=True)

        fallback_message = (
            "Eita, Lenda! 🎸 Deu uma microfonia nervosa aqui no meu sistema e "
            "perdi a conexão com o estúdio. 🔌"
            "Pode repetir a pergunta, por favor? Se continuar falhando, "
            "tente novamente em alguns minutos enquanto eu afino as cordas!"
        )

        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=fallback_message
        )


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
    except HTTPException:
        raise
    except Exception:
        logger.error("🔥 ERRO CRÍTICO AO LIMPAR SESSÃO", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao limpar sessão!",
        )
