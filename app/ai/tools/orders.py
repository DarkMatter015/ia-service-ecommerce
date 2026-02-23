import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embeddings
from app.core.config import settings
from app.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class OrdersTools:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()
        self.repo = ProductRepository(db)

    # Pedidos (Async)
    async def fetch_order_from_java(self, order_id: str, user_token: str):
        """Consulta a API Java para pegar dados do pedido"""
        url = f"{settings.BACKEND_URL}/orders/ai/{order_id}"
        headers = {"Authorization": user_token} if user_token else {}

        async with httpx.AsyncClient() as client:
            try:
                logger.info("Buscando pedido na API Java...")
                response = await client.get(url, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    logger.info("Pedido encontrado na API Java.")
                    return response.json()
                elif response.status_code == 401 or response.status_code == 403:
                    logger.warning("Acesso negado ao pedido.")
                    return {
                        "error": "Acesso negado. Você não tem permissão para ver este pedido."
                    }
                elif response.status_code == 404:
                    logger.warning("Pedido não encontrado.")
                    return {"error": "Pedido não encontrado."}
                else:
                    logger.error(f"Erro no sistema de pedidos: {response.status_code}")
                    return {
                        "error": f"Erro no sistema de pedidos: {response.status_code}"
                    }
            except Exception as e:
                logger.error(f"Falha ao conectar no sistema de pedidos: {str(e)}")
                return {"error": f"Falha ao conectar no sistema de pedidos: {str(e)}"}
