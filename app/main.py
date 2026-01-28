from fastapi import FastAPI
from app.api.v1 import chat, ingestion
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from app.core.rabbitmq import start_rabbitmq_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("🚀 Iniciando RiffHouse AI...")
    
    # Inicia o RabbitMQ em background task para não bloquear o boot da API
    # Salvamos a task para manter referência
    task = asyncio.create_task(start_rabbitmq_consumer())
    
    yield
    
    # --- Shutdown ---
    print("🛑 Desligando serviços...")
    # O aio_pika gerencia o shutdown gracioso na conexão robusta, 
    # mas aqui você poderia cancelar a task se necessário.

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

origins = [
    "*"
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

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "RiffHouse AI"}