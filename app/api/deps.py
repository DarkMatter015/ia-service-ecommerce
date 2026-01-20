from typing import AsyncGenerator
from app.core.database import SessionLocal


async def get_db() -> AsyncGenerator:
    """
    Cria uma sessão de banco de dados para cada requisição
    e a fecha automaticamente quando a requisição termina.
    """
    async with SessionLocal() as db:
        yield db
