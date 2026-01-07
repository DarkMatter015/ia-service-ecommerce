from fastapi import FastAPI
from app.api.v1 import chat, ingestion
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.PROJECT_NAME)

origins = [
    "http://localhost:5173", # Porta padrão do Vite
    "http://localhost:8080", # porta do backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["ingestion"])

@app.get("/")
def health_check():
    return {"status": "ok", "service": "RiffHouse AI"}