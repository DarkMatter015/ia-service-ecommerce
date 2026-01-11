import json

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.services.llm_factory import get_llm
from app.services.tools import EcommerceTools


class AgentService:
    def __init__(self, db: Session, user_token: str):
        self.db = db
        self.llm = get_llm()
        self.user_token = user_token
        self.tools = EcommerceTools(db)

    async def handle_request(self, user_message: str):
        # 1. Definição das Tools (Schemas JSON para a LLM entender)
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "search_catalog",
                    "description": "Busca produtos, preços e recomendações no catálogo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "O termo de busca, ex: 'guitarra fender'",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_order_status",
                    "description": "Verifica o status e detalhes de um pedido pelo ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "O número/ID do pedido, ex: '12345'",
                            }
                        },
                        "required": ["order_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "product_analytics",
                    "description": "Use para responder perguntas sobre QUANTIDADE, MÉDIA de preços, ou RANKING (mais caros, mais baratos, maior estoque). NÃO use para buscar descrições simples.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": ["count", "average_price", "ranking"],
                                "description": "O tipo de cálculo necessário.",
                            },
                            "category": {
                                "type": "string",
                                "description": "A categoria para filtrar. Ex: 'Violões', 'Guitarras', 'Baterias', 'Teclados', etc.",
                            },
                            "order_by": {
                                "type": "string",
                                "enum": ["price_desc", "price_asc", "stock_desc"],
                                "description": "Critério de ordenação para rankings.",
                            },
                            "limit": {
                                "type": "string",
                                "description": "Quantos itens retornar no ranking (padrão 5).",
                            },
                        },
                        "required": ["intent"],
                    },
                },
            },
        ]

        # 2. Bind das tools no modelo (O Groq/Llama suporta isso nativamente)
        llm_with_tools = self.llm.bind_tools(tools_schema)

        # 3. Prompt do Sistema
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Você é o assistente inteligente da RiffHouse. "
                    "Use as ferramentas disponíveis para responder. "
                    "Se perguntarem de produtos, busque no catálogo. "
                    "Se perguntarem de pedidos, busque as informações do pedido. "
                    "Se perguntarem de análise de produtos, use as ferramentas de análise. "
                    "Se for apenas um 'oi' ou algo que não tenha relação nenhuma com a RiffHouse, responda educadamente sem usar ferramentas.",
                ),
                ("user", "{input}"),
            ]
        )

        # 4. Primeira Chamada (LLM Pensa)
        chain = prompt | llm_with_tools
        response_msg = chain.invoke({"input": user_message})

        # 5. Loop de Execução de Ferramentas
        # Se a IA decidiu chamar uma ferramenta (tool_calls não está vazio)
        if response_msg.tool_calls:
            # Lista para acumular resultados
            tool_outputs = []

            for tool_call in response_msg.tool_calls:
                fn_name = tool_call["name"]
                args = tool_call["args"]
                content_result = ""

                print(f"🤖 IA Decidiu usar: {fn_name} com args: {args}")

                # Roteamento manual
                if fn_name == "search_catalog":
                    content_result = self.tools.search_catalog_tool(args["query"])

                elif fn_name == "check_order_status":
                    data = await self.tools.fetch_order_from_java(
                        order_id=str(args["order_id"]), 
                        user_token=self.user_token
                    )
                    content_result = str(data)

                elif fn_name == "product_analytics":
                    content_result = self.tools.product_analytics(
                        intent=args.get("intent"),
                        category=args.get("category"),
                        order_by=args.get("order_by"),
                        limit=args.get("limit", "5"),
                    )

                # Cria a mensagem de resposta da ferramenta
                tool_outputs.append(
                    ToolMessage(
                        content=str(content_result), 
                        tool_call_id=tool_call["id"]
                    )
                )

            # TODO: FIX ME Alucination when asks abou most expensive products
            # 6. Segunda Chamada (LLM Gera a Resposta Final com os dados)
            # Reconstruímos o histórico: System -> User -> AI (com intenção de tool) -> Tool Output
            final_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "Você é o assistente RiffHouse. Responda ao usuário com base nas informações abaixo.",
                    ),
                    ("user", user_message),
                    (response_msg),  # A mensagem que disse "vou chamar a tool"
                    *tool_outputs,  # O resultado da tool (JSON do pedido ou Texto dos produtos)
                ]
            )

            final_chain = final_prompt | self.llm
            final_response = final_chain.invoke({})
            return final_response.content
        
        else:
            print("🤖 IA está response sem utilizar dados da RiffHouse")
            # Se a IA não chamou tools (ex: "Oi tudo bem?"), devolve a resposta direta
            return response_msg.content
