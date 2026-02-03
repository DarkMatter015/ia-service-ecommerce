from typing import Any, Dict, List

from sqlalchemy import select, func, text, cast, Numeric, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProductEmbedding
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[ProductEmbedding]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ProductEmbedding)

    async def get_products_for_sync(self) -> List[Dict[str, Any]]:
        """
        Fetches products from the legacy 'tb_product' table joined with 'tb_category'.
        """
        result = await self.db.execute(
            text("""
            SELECT 
                p.id, 
                p.name, 
                p.description, 
                p.price, 
                p.quantity_available_in_stock, 
                p.category_id, 
                p.deleted_at,
                c.name as category_name
            FROM tb_product p
            LEFT JOIN tb_category c ON p.category_id = c.id
        """)
        )
        return result.mappings().all()

    async def exists_by_product_id(self, product_id: int) -> bool:
        result = await self.db.execute(
            select(self.model).filter_by(product_id=product_id)
        )
        return result.scalars().first() is not None

    # --- Métodos de Busca Híbrida ---
    async def search_by_vector(
        self, query_vector: List[float], limit: int
    ) -> List[ProductEmbedding]:
        """
        Searches for products using vector similarity.
        """
        stmt = (
            select(self.model)
            .order_by(self.model.embedding.cosine_distance(query_vector))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search_by_keyword(self, query: str, limit: int) -> List[ProductEmbedding]:
        """
        Searches for products using keyword matching.
        """
        stmt = (
            select(self.model)
            .filter(text("search_vector @@ plainto_tsquery('portuguese', :q)"))
            .params(q=query)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    # --- Métodos de Analytics (Ranking/Count) ---
    async def average_price(self, category: str = None):
        price_field = cast(self.model.metadata_["price"].cast(Text), Numeric)
        query = select(func.avg(price_field))
        if category:
            query = query.filter(
                self.model.metadata_["category"].cast(Text).ilike(f"%{category}%")
            )
        result = await self.db.execute(query)
        return result.scalar()

    async def count_by_category(self, category: str) -> int:
        result = await self.db.execute(
            select(func.count(ProductEmbedding.id))
            .filter(text("metadata->>'category' ILIKE :cat"))
            .params(cat=f"%{category}%")
        )
        return result.scalar()

    async def list_products(
        self,
        category: str = None,
        order_by_field: str = None,
        order_direction: str = "asc",
        limit: int = 5,
    ):
        query = select(self.model)

        # Filtro
        if category:
            query = query.filter(text("metadata->>'category' ILIKE :cat")).params(
                cat=f"%{category}%"
            )

        # Ordenação
        if order_by_field:
            direction = "DESC" if order_direction.lower() == "desc" else "ASC"
            cast_type = "int" if order_by_field == "stock" else "numeric"
            query = query.order_by(
                text(f"(metadata->>'{order_by_field}')::{cast_type} {direction}")
            )

        result = await self.db.execute(query.limit(limit))
        return result.scalars().all()
        
    async def get_by_product_id(self, product_id: int) -> ProductEmbedding:
        result = await self.db.execute(
            select(self.model).filter_by(product_id=product_id)
        )
        return result.scalars().first()