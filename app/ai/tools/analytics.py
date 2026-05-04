import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embeddings
from app.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class AnalyticsTools:
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
            logger.info("Contando produtos...")
            # Ex: "Quantos produtos tem na categoria X?"
            total = (
                await self.repo.count_by_category(category)
                if category
                else await self.repo.count()
            )
            return f"Total encontrado: {total} produtos."

        elif intent == "average_price":
            logger.info("Calculando preço médio...")
            # Ex: "Qual a média de preço das guitarras?"
            avg = await self.repo.average_price(category)
            val = round(avg, 2) if avg else 0
            return f"O preço médio {'da categoria ' + category if category else 'geral'} é R$ {val}."

        elif intent == "ranking":
            logger.info("Gerando ranking de produtos...")
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
                logger.warning(
                    "Nenhum produto encontrado no banco de dados com esses critérios."
                )
                return (
                    "Nenhum produto encontrado no banco de dados com esses critérios."
                )

            logger.info("Produtos encontrados no banco de dados com esses critérios.")
            return "\n".join(
                [
                    f"{i + 1}º: {p.content.split('. ')[0]} | R$ {p.metadata_['price']} | Estoque: {p.metadata_['stock']}"
                    for i, p in enumerate(results)
                ]
            )

        logger.error("Não entendi o tipo de análise solicitada.")
        return "Não entendi o tipo de análise solicitada."
