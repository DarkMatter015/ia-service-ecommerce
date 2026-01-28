from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import ProductEmbedding
from app.services.llm_factory import get_embeddings
from app.repositories.product import ProductRepository
from sqlalchemy import select

class ProductSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)
        self.embeddings = get_embeddings()

    async def upsert_product(self, product_data: dict):
        """
        Recebe o JSON do RabbitMQ, gera vetor e Salva/Atualiza no banco.
        """
        try:
            # 1. Extrair dados do JSON (Ajuste as chaves conforme seu Java envia)
            p_id = product_data.get("id")
            name = product_data.get("name")
            desc = product_data.get("description")
            price = float(product_data.get("price") or 0)
            stock = int(product_data.get("quantityAvailableInStock") or 0)
            category = product_data.get("category")

            # 2. Criar Texto Rico
            content_text = f"Produto: {name}. Descrição: {desc}."

            # 3. Gerar Vetor (Async via executor para não travar)
            # Dica: Em produção, faça tratamento de erro aqui caso o Google falhe
            vector = await self.embeddings.aembed_query(content_text)

            # 4. Verificar se existe (Lógica de Upsert manual ou use a do Postgres)
            # Aqui faremos manual para clareza
            stmt = select(ProductEmbedding).where(ProductEmbedding.product_id == p_id)
            result = await self.db.execute(stmt)
            existing_product = result.scalar_one_or_none()

            metadata = {
                "price": price,
                "category": category,
                "stock": stock
            }

            if existing_product:
                print(f"🔄 Atualizando Produto ID {p_id}...")
                existing_product.content = content_text
                existing_product.embedding = vector
                existing_product.metadata_ = metadata
                # search_vector atualiza sozinho via Trigger no banco
            else:
                print(f"✨ Criando Produto ID {p_id}...")
                new_prod = ProductEmbedding(
                    product_id=p_id,
                    content=content_text,
                    embedding=vector,
                    metadata_=metadata
                )
                self.db.add(new_prod)

            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            print(f"❌ Erro ao sincronizar produto {product_data.get('id')}: {e}")
            raise e