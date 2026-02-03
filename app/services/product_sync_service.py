from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product_model import ProductEmbedding
from app.ai.factory import get_embeddings
from app.repositories.product_repository import ProductRepository
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from google.api_core.exceptions import ResourceExhausted
import logging

logger = logging.getLogger(__name__)


class ProductSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)
        self.embeddings = get_embeddings()

    @retry(
        retry=retry_if_exception_type(ResourceExhausted),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,  # Importante: Se falhar 5x, sobe o erro para o RabbitMQ mandar pra DLQ
    )
    async def _generate_embedding_safe(self, text: str):
        """Método auxiliar protegido com Retry"""
        # CORREÇÃO: Usamos este método para garantir que o retry funcione
        return await self.embeddings.aembed_query(text)

    async def upsert_product(self, product_data: dict):
        try:
            # 1. Validação Básica (Evita erros bobos)
            p_id = product_data.get("id")
            name = product_data.get("name")

            if not p_id or not name:
                logger.warning(
                    f"⚠️ Produto ignorado por falta de ID ou Nome: {product_data}"
                )
                return False  # Retorna sucesso para tirar da fila, pois não há salvação

            # Tratamento de Nulos (Null Safety)
            desc = product_data.get("description") or ""
            price = float(product_data.get("price") or 0)
            stock = int(product_data.get("stock") or 0)
            category = product_data.get("category") or "Geral"

            # 2. Criar Texto Rico (Limpeza)
            # Removemos espaços extras e garantimos que não entre "None" no texto
            content_text = (
                f"Produto: {name}. Categoria: {category}. Descrição: {desc}".strip()
            )

            # 3. Gerar Vetor
            vector = await self._generate_embedding_safe(content_text)

            # 4. Verificar se existe
            existing_product = await self.repo.get_by_product_id(p_id)

            # Metadata para filtros
            metadata = {"price": price, "category": category, "stock": stock}

            if existing_product:
                logger.info(f"🔄 Atualizando Produto ID {p_id}...")
                # Atualiza campos
                existing_product.content = content_text
                existing_product.embedding = vector
                existing_product.metadata_ = metadata
            else:
                logger.info(f"✨ Criando Produto ID {p_id}...")
                new_prod = ProductEmbedding(
                    product_id=p_id,
                    content=content_text,
                    embedding=vector,
                    metadata_=metadata,
                )
                self.db.add(new_prod)

            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"❌ Erro ao sincronizar produto {product_data.get('id')}: {e}",
                exc_info=True,
            )
            raise e
