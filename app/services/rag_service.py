from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.product import ProductEmbedding
from app.services.llm_factory import get_llm, get_embeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm()
        self.embeddings = get_embeddings()

    def get_similar_products(self, query: str, limit: int = 3):
        # 1. Gerar vetor da pergunta do usuário
        query_vector = self.embeddings.embed_query(query)
        
        # 2. Busca vetorial no Postgres (Cosine Distance)
        # O operador <=> é a distância de cosseno no pgvector
        stmt = select(ProductEmbedding).order_by(
            ProductEmbedding.embedding.cosine_distance(query_vector)
        ).limit(limit)
        
        results = self.db.execute(stmt).scalars().all()
        return results

    def answer_question(self, query: str):
        # 1. Recuperar contexto
        products = self.get_similar_products(query)
        
        # Se não achou nada relevante (opcional: lógica de corte por score)
        if not products:
            return "Desculpe, não encontrei produtos relacionados à sua dúvida."

        # 2. Montar contexto em texto
        context_str = "\n\n".join([f"Produto: {p.content}" for p in products])

        # 3. Prompt Engineering
        template = """
        Você é um assistente útil do e-commerce RiffHouse.
        Use APENAS o contexto abaixo para responder à pergunta do cliente.
        Se a resposta não estiver no contexto, diga que não sabe. Não invente.
        
        Contexto:
        {context}
        
        Pergunta: 
        {question}
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 4. Chain (LangChain Expression Language - LCEL)
        chain = prompt | self.llm | StrOutputParser()
        
        return chain.invoke({"context": context_str, "question": query})