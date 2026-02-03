from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.ai.factory import get_embeddings

import logging

logger = logging.getLogger(__name__)


class CatalogTools:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()
        self.repo = ProductRepository(db)

    # Busca Híbrida (Texto + Vetor)
    async def search_catalog_tool(self, query: str):
        results = await self.hybrid_search(query)

        if not results:
            logger.warning(
                "Nenhum produto encontrado no banco de dados com esses critérios."
            )
            return "Nenhum produto relevante encontrado."

        logger.info("Produtos encontrados no banco de dados com esses critérios.")
        return "\n\n".join(
            [f"Produto: {p.content} (Preço/Info: {p.metadata_})" for p in results]
        )

    async def hybrid_search(self, query: str, limit: int = 5):
        """
        Executa busca híbrida usando RRF (Reciprocal Rank Fusion).
        """
        scores = {}

        # Busca Vetorial (Semântica)
        query_vector = get_embeddings().embed_query(query)
        vector_results = await self.repo.search_by_vector(query_vector, limit * 2)

        # Busca Keyword (Full-Text Search)
        keyword_results = await self.repo.search_by_keyword(query, limit * 2)

        # Fusão RRF (Reciprocal Rank Fusion)
        product_map = {p.id: p for p in vector_results + keyword_results}

        # Calcula scores
        self.calculate_rrf_score(vector_results, scores)
        self.calculate_rrf_score(keyword_results, scores)

        # Ordenar pelo score final (Decrescente)
        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:limit]
        return [product_map[pid] for pid in sorted_ids]

    def calculate_rrf_score(self, results, scores, k=60):
        """
        Calcula o score final usando RRF (Reciprocal Rank Fusion).
        k: Constante de suavização.
        """
        for rank, prod in enumerate(results):
            if prod.id not in scores:
                scores[prod.id] = 0
            scores[prod.id] += 1 / (k + rank + 1)
