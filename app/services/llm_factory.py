from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

def get_llm():
    """Retorna o modelo de Chat (Groq - Llama 3)"""
    return ChatGroq(
        temperature=0, 
        model="llama-3.3-70b-versatile",
        groq_api_key=settings.GROQ_API_KEY
    )

def get_embeddings():
    """Retorna o modelo de Embeddings (Google)"""
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=settings.GOOGLE_API_KEY
    )