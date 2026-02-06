from langchain_groq import ChatGroq
from app.core.config import settings


def get_llm():
    """Retorna o modelo de Chat (Groq - Llama 3)"""
    return ChatGroq(
        temperature=0,
        model="llama-3.3-70b-versatile",
        groq_api_key=settings.GROQ_API_KEY,
    )
