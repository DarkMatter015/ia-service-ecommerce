from fastapi import FastAPI
from app.api.v1 import chat, ingestion
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.rabbitmq import start_rabbitmq_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("🚀 Iniciando RiffHouse AI...")
    
    # 1. Iniciamos o consumidor e PEGAMOS a conexão
    connection = await start_rabbitmq_consumer()
    
    # 2. SALVAMOS A CONEXÃO NO ESTADO DO APP
    app.state.rabbitmq_connection = connection
    
    yield
    
    # --- Shutdown ---
    print("🛑 Desligando serviços...")
    try:
        # Fechamos a conexão graciosamente ao desligar a API
        await app.state.rabbitmq_connection.close()
        print("🐰 Conexão RabbitMQ fechada.")
    except Exception as e:
        print(f"Erro ao fechar RabbitMQ: {e}")

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