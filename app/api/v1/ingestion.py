from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.product import ProductEmbedding
from app.repositories.product import ProductRepository
from app.services.llm_factory import get_embeddings

router = APIRouter()


@router.post("/sync-products")
async def sync_products(db: AsyncSession = Depends(get_db)):
    """
    Lê produtos da tabela original (Java) e gera vetores na tabela de IA.
    ATENÇÃO: Este é um script simples. Em produção, use filas (RabbitMQ).
    """
    repo = ProductRepository(db)
    try:
        # 1. Buscar produtos na tabela original (tb_product) via Repositório
        products = await repo.get_products_for_sync()

        if not products:
            return {"message": "Nenhum produto encontrado na tabela tb_product."}

        embeddings_model = get_embeddings()
        count = 0

        for prod in products:
            # 2. Verificar se já existe vetor para esse produto (evitar duplicação)
            if await repo.exists_by_product_id(prod["id"]):
                continue

            # 3. Criar o texto rico para vetorização
            cat_name = (
                prod["category_name"] if prod["category_name"] else "Sem Categoria"
            )
            content_text = f"Produto: {prod['name']}. Descrição: {prod['description']}"

            # 4. Gerar Vetor (Chamada API Google)
            vector = embeddings_model.embed_query(content_text)

            # 5. Salvar no Banco
            new_embedding = ProductEmbedding(
                product_id=prod["id"],
                embedding=vector,
                content=content_text,
                metadata_={
                    "price": float(prod["price"]),
                    "category": cat_name,
                    "stock": int(prod["quantity_available_in_stock"]),
                },
            )
            # Usando db session direto para batch (ou poderíamos adicionar métodos de batch ao repo)
            db.add(new_embedding)
            count += 1

        await db.commit()
        return {"status": "success", "products_vectorized": count}

    except Exception as e:
        await db.rollback()
        # Logar o erro real no console para debug
        print(f"Erro na ingestão: {e}")
        raise HTTPException(status_code=500, detail=str(e))
