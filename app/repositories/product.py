from typing import Any, Dict, List

from sqlalchemy import select, func, text, cast, Numeric, Text
from sqlalchemy.orm import Session

from app.models.product import ProductEmbedding
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[ProductEmbedding]):
    def __init__(self, db: Session):
        super().__init__(db, ProductEmbedding)

    def get_products_for_sync(self) -> List[Dict[str, Any]]:
        """
        Fetches products from the legacy 'tb_product' table joined with 'tb_category'.
        """
        return (
            self.db.execute(
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
            .mappings()
            .all()
        )

    def exists_by_product_id(self, product_id: int) -> bool:
        return (
            self.db.query(self.model).filter_by(product_id=product_id).first()
            is not None
        )

    # --- Métodos de Busca Híbrida ---
    def search_by_vector(
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

        return self.db.execute(stmt).scalars().all()

    def search_by_keyword(self, query: str, limit: int) -> List[ProductEmbedding]:
        """
        Searches for products using keyword matching.
        """
        stmt = (
            select(self.model)
            .filter(text("search_vector @@ plainto_tsquery('portuguese', :q)"))
            .params(q=query)
            .limit(limit)
        )

        return self.db.execute(stmt).scalars().all()

    # --- Métodos de Analytics (Ranking/Count) ---
    def average_price(self, category: str = None):
        price_field = cast(self.model.metadata_['price'].cast(Text), Numeric)
        query = select(func.avg(price_field))
        if category:
            query = query.filter(self.model.metadata_['category'].cast(Text).ilike(f"%{category}%"))
        return self.db.execute(query).scalar()

    def count_by_category(self, category: str) -> int:
        return self.db.execute(
            select(func.count(ProductEmbedding.id))
            .filter(text("metadata->>'category' ILIKE :cat"))
            .params(cat=f"%{category}%")
        ).scalar()

    def list_products(
        self,
        category: str = None,
        order_by_field: str = None,
        order_direction: str = "asc",
        limit: int = 5,
    ):
        query = self.db.query(self.model)

        # Filtro
        if category:
            query = query.filter(text("metadata->>'category' ILIKE :cat")).params(
                cat=f"%{category}%"
            )

        # Ordenação
        if order_by_field:
            direction = "DESC" if order_direction.lower() == "desc" else "ASC"
            # Cast seguro para numeric ou int dependendo do campo
            cast_type = "int" if order_by_field == "stock" else "numeric"
            query = query.order_by(
                text(f"(metadata->>'{order_by_field}')::{cast_type} {direction}")
            )

        return query.limit(limit).all()
