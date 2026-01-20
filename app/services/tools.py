import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.product import ProductRepository
from app.services.llm_factory import get_embeddings


class EcommerceTools:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()
        self.repo = ProductRepository(db)

    # Analytics (Ranking, Count, Avg)
    async def product_analytics(
        self,
        intent: str,
        category: str = None,
        order_by: str = None,
        limit: str = "5",
    ):
        """
        Executa análises quantitativas no banco de dados.

        intent: 'count' (quantidade), 'average_price' (média), 'ranking' (top X).
        category: Filtro opcional de categoria.
        order_by: Para ranking ('price_desc', 'price_asc', 'stock_desc').
        """
        try:
            limit_val = int(limit)
        except ValueError:
            limit_val = 5

        if intent == "count":
            # Ex: "Quantos produtos tem na categoria X?"
            total = (
                await self.repo.count_by_category(category)
                if category
                else await self.repo.count()
            )
            return f"Total encontrado: {total} produtos."

        elif intent == "average_price":
            # Ex: "Qual a média de preço das guitarras?"
            avg = await self.repo.average_price(category)
            val = round(avg, 2) if avg else 0
            return f"O preço médio {'da categoria ' + category if category else 'geral'} é R$ {val}."

        elif intent == "ranking":
            # Ex: "Quais as 3 guitarras mais caras?"
            field = "price"
            direction = "desc"

            if order_by == "price_asc":
                direction = "asc"
            elif order_by == "stock_desc":
                field = "stock"

            results = await self.repo.list_products(
                category=category,
                order_by_field=field,
                order_direction=direction,
                limit=limit_val,
            )

            if not results:
                return (
                    "Nenhum produto encontrado no banco de dados com esses critérios."
                )

            return "\n".join(
                [
                    f"{i + 1}º: {p.content.split('. ')[0]} | R$ {p.metadata_['price']} | Estoque: {p.metadata_['stock']}"
                    for i, p in enumerate(results)
                ]
            )

        return "Não entendi o tipo de análise solicitada."

    # Busca Híbrida (Texto + Vetor)
    async def search_catalog_tool(self, query: str):
        results = await self.hybrid_search(query)

        if not results:
            return "Nenhum produto relevante encontrado."

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

    # Pedidos (Async)
    async def fetch_order_from_java(self, order_id: str, user_token: str):
        """Consulta a API Java para pegar dados do pedido"""
        url = f"{settings.BACKEND_URL}/orders/ai/{order_id}"
        headers = {"Authorization": user_token} if user_token else {}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401 or response.status_code == 403:
                    return {
                        "error": "Acesso negado. Você não tem permissão para ver este pedido."
                    }
                elif response.status_code == 404:
                    return {"error": "Pedido não encontrado."}
                else:
                    return {
                        "error": f"Erro no sistema de pedidos: {response.status_code}"
                    }
            except Exception as e:
                return {"error": f"Falha ao conectar no sistema de pedidos: {str(e)}"}
