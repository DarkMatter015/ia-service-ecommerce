from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db
from app.models.product import ProductEmbedding
from app.services.llm_factory import get_embeddings

router = APIRouter()


@router.post("/sync-products")
def sync_products(db: Session = Depends(get_db)):
    """
    Lê produtos da tabela original (Java) e gera vetores na tabela de IA.
    ATENÇÃO: Este é um script simples. Em produção, use filas (RabbitMQ).
    """
    try:
        # 1. Buscar produtos na tabela original (tb_product)
        stmt = text("""
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
        result = db.execute(stmt)
        products = result.mappings().all()

        if not products:
            return {"message": "Nenhum produto encontrado na tabela tb_product."}

        embeddings_model = get_embeddings()
        count = 0

        for prod in products:
            # 2. Verificar se já existe vetor para esse produto (evitar duplicação)
            exists = db.query(ProductEmbedding).filter_by(product_id=prod["id"]).first()
            if exists:
                continue

            # 3. Criar o texto rico para vetorização
            # Juntamos tudo para a IA entender o contexto global do produto
            cat_name = (
                prod["category_name"] if prod["category_name"] else "Sem Categoria"
            )
            content_text = f"""Produto: {prod["name"]}. 
            Categoria: {cat_name}. 
            Descrição: {prod["description"]}. 
            Preço: R$ {prod["price"]}.
            Quantidade em estoque: {prod["quantity_available_in_stock"]}.
            """

            # 4. Gerar Vetor (Chamada API Google)
            vector = embeddings_model.embed_query(content_text)

            # 5. Salvar no Banco
            new_embedding = ProductEmbedding(
                product_id=prod["id"],
                embedding=vector,
                content=content_text,
                metadata_={"price": float(prod["price"]), "category": cat_name},
            )
            db.add(new_embedding)
            count += 1

        db.commit()
        return {"status": "success", "products_vectorized": count}

    except Exception as e:
        db.rollback()
        # Logar o erro real no console para debug
        print(f"Erro na ingestão: {e}")
        raise HTTPException(status_code=500, detail=str(e))
