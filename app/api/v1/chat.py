from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.deps import get_db
from app.services.rag_service import RAGService

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/message", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        service = RAGService(db)
        answer = service.answer_question(request.message)
        return ChatResponse(response=answer)
    except Exception as e:
        # Em produção, logue o erro real e retorne algo genérico
        print(e)
        raise HTTPException(status_code=500, detail=str(e))