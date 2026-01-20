from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api.deps import get_db
from app.services.agent_service import AgentService

router = APIRouter()

security = HTTPBearer(auto_error=False)


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
        # Em produção, logue o erro real e retorne algo genérico
        print(f"Erro no Chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
