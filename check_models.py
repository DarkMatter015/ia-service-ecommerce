import google.genai as genai
import os
from dotenv import load_dotenv
from app.services.llm_factory import get_embeddings

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("🔍 Listando modelos de Embedding disponíveis para sua chave:")

try:
    # # 2. Itera sobre a lista de modelos
    for model in client.models.list():
        # Filtra apenas modelos de embedding para facilitar a leitura
        if "embedding" in model.name:
            print(f"✅ Nome: {model.name}")
            print(f"   Display Name: {model.display_name}") # Opcional
    # e = get_embeddings()
    # print(e.model)

except Exception as e:
    print(f"❌ Erro ao listar modelos: {e}")