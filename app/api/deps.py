from typing import Generator
from app.core.database import SessionLocal

def get_db() -> Generator:
    """
    Cria uma sessão de banco de dados para cada requisição 
    e a fecha automaticamente quando a requisição termina.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()