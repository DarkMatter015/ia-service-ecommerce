# 🧠 RiffHouse AI — Intelligent Agent Service

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-High_Performance-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LPU_Inference-orange?style=for-the-badge)

![LangChain](https://img.shields.io/badge/LangChain-Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Llama 3](https://img.shields.io/badge/Model-Llama_3.3_70B-blue?style=for-the-badge)
![Google Gemini](https://img.shields.io/badge/Embeddings-Google_GenAI-4285F4?style=for-the-badge&logo=google)

</div>

## 📖 Sobre o Projeto

**RiffHouse AI** é um microsserviço de inteligência artificial projetado para atuar como o cérebro da plataforma de e-commerce RiffHouse. Construído com **Python e FastAPI**, ele fornece uma API para processamento de linguagem natural (NLP).

O serviço implementa uma arquitetura **RAG (Retrieval-Augmented Generation)**, permitindo que o Agente de IA "converse" com o catálogo de produtos e dados operacionais em tempo real, oferecendo recomendações precisas e suporte automatizado ao cliente.

---

## 🏗️ Arquitetura de IA e Decisões Técnicas

### ⚡ Inference Engine: Groq & Llama 3.3
Utilizei a **GroqCloud** para inferência, aproveitando suas LPUs (Language Processing Units) para atingir velocidades de tokenização extremamente altas.
* **Modelo:** `llama-3.3-70b-versatile`. Um modelo open-source robusto, capaz de raciocínio complexo e nuances linguísticas, ideal para vendas consultivas.

### 🔍 Vector Search & Embeddings
Para a busca semântica (RAG), evitei a complexidade de manter um banco vetorial separado (como Pinecone) e optei pela integração nativa:
* **Vector Store:** **PostgreSQL com `pgvector`**. Isso unifica a stack de dados, permitindo joins entre dados relacionais e vetoriais na mesma infraestrutura.
* **Embeddings:** **Google GenAI (`gemini-embedding-001`)**. Modelo eficiente para transformar descrições de produtos em vetores densos.

### 🛠️ Agent Tools (Function Calling)
O modelo não apenas "gera texto", ele toma decisões sobre qual ferramenta usar com base na pergunta do usuário:
1.  **search_catalog:** Busca semântica no catálogo (ex: "Guitarra Startocaster", "Quero uma guitarra azul barata").
2.  **check_order_status::** Consulta SQL direta para status de pedidos (ex: "Qual o status do meu pedido #123?").
3.  **product_analytics:** Executa agregações SQL para responder perguntas complexas (ex: "Qual é a média de preço das baterias?").

---

## 🚀 Funcionalidades

### 🛒 Assistente de Vendas (RAG)
* Entende intenção de compra e recomenda produtos baseados em características subjetivas (timbre, estilo musical, nível de habilidade).
* Justifica a recomendação com dados técnicos do produto.

### 📊 Consultas Analíticas e Operacionais
* **Rastreio:** Verifica status, data de entrega e detalhes de pedidos específicos via ID.
* **Agregação de Dados:** Responde perguntas sobre quantidade de estoque, médias de preço e rankings (produtos mais caros/baratos) em tempo real.

### 🔄 Sincronização de Dados Automática
* Escuta eventos do RabbitMQ para atualizar o catálogo em tempo real, reindexando novos produtos adicionados ao banco de dados relacional, garantindo que o Agente sempre conheça o catálogo atualizado.

---

## ⚙️ Configuração e Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto seguindo o modelo:

```env
# Conexão com o Banco de Dados (Deve ter a extensão vector ativada)
DATABASE_URL=postgresql://user:password@localhost:5432/riffhouse

# Chaves de API para Modelos de IA
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...

# Endereço do Backend Java (para realizar buscas de pedidos)
BACKEND_URL=http://localhost:8080

# API
MELHOR_ENVIO_API_TOKEN=

DB_USERNAME=postgres
DB_PASSWORD=postgres

JWT_SECRET=
```

---

## ⚡ Como Rodar

### 🐳 Via Docker (Recomendado)
Sobe toda a infraestrutura (API, Banco e Front End) com um comando:

```bash
  # Clone o repositório
  git clone https://github.com/DarkMatter015/ai-service-ecommerce.git
  cd ai-service-ecommerce
  
  # 2. Inicie os serviços
  docker-compose up --build -d
```

✅ API AI: http://localhost:8000 | FrontEnd: http://localhost:80

### Localmente

#### Pré-requisitos
*  Python 3.10+
*  PostgreSQL com extensão `vector` instalada.

### 1️⃣ Instalação

```bash
  # Clone o repositório
  git clone https://github.com/DarkMatter015/ai-service-ecommerce.git
  cd ai-service-ecommerce
  
  # Crie um ambiente virtual
  python -m venv venv
  source venv/bin/activate  # Linux/Mac
  # venv\Scripts\activate   # Windows
  
  # Instale as dependências
  pip install -r requirements.txt
```

### 2️⃣ Execução
O servidor iniciará na porta `8000`.

```bash
  uvicorn app.main:app --reload
```

👉 **Swagger UI:** Acesse `http://localhost:8000/docs` para testar os endpoints interativamente.

---

## 🛣️ Roadmap e Melhorias Futuras
*  [ ] **Memória de Conversa (Chat History):** Implementar Redis para armazenar o contexto da conversa, permitindo perguntas de acompanhamento ("E quanto custa essa que você mostrou?").
*  [ ] **Cálculo de Frete:** Integração da Tool de IA com a API de CEP.
*  [X] **Sync via Eventos:** Substituir o endpoint `/sync` manual por um consumidor RabbitMQ, ouvindo eventos de `product.created` e `product.updated` do backend Java.

---

## 👨‍💻 Autor

<table style="border: none;">
  <tr>
    <td width="100px" align="center">
      <img src="https://github.com/DarkMatter015.png" width="100px" style="border-radius: 50%;" alt="Avatar do Lucas"/>
    </td>
    <td style="padding-left: 15px;">
      <strong>Lucas Matheus de Camargo</strong><br>
      <i>Desenvolvedor Full Stack | QA</i><br>
      <br>
      <a href="https://www.linkedin.com/in/lucas-matheus-de-camargo-49a315236/" target="_blank">
        <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white" alt="LinkedIn Badge">
      </a>
      <a href="https://github.com/DarkMatter015" target="_blank">
        <img src="https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white" alt="GitHub Badge">
      </a>
    </td>
  </tr>
</table>


---

<div align="center"> <sub>Feito com 🐍 e IA por Lucas Matheus.</sub> </div>
