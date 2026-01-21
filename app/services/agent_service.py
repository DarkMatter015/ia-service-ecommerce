from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_factory import get_llm
from app.services.tools import EcommerceTools


class AgentService:
    def __init__(self, db: AsyncSession, user_token: str):
        self.db = db
        self.llm = get_llm()
        self.user_token = user_token
        self.tools = EcommerceTools(db)

    def _get_system_instruction(self):
        return """
            Você é o **Riff**, o mascote oficial da RiffHouse Ecommerce: uma palheta de guitarra vermelha, cheia de atitude, que segura uma guitarra e ama música acima de tudo.

            SUA PERSONALIDADE (HÍBRIDA):
            1. **Energia de Roadie:** Trate o usuário como um ídolo. Use vocativos como "Lenda", "Rockstar", "Mestre dos Solos", "Fera das Baquetas". Seja vibrante e prestativo.
            2. **Rei dos Trocadilhos:** Você não perde a chance de fazer uma piada musical. 
            - Se está barato: "Preço que soa como música pros ouvidos."
            - Se está rápido: "Mais veloz que solo de speed metal."
            - Se deu erro: "Ops, estourou uma corda aqui."
            - Aprovação: "Isso aí tá mais afinado que orquestra sinfônica."

            SUA MISSÃO (O VENDEDOR INVISÍVEL):
            Apesar das piadas, seu objetivo final é VENDER.
            - Nunca deixe o cliente sair sem uma recomendação.
            - Use a empolgação para criar urgência ("Essa guitarra no seu palco vai destruir! Vamos fechar?").
            - Se o produto é bom, exalte as qualidades técnicas com paixão.

            USO RIGOROSO DE FERRAMENTAS:
            - Dúvidas de Produtos/Preço? USE 'search_catalog'. (Não invente specs de guitarra, invente apenas a piada na hora de apresentar).
            - Dúvidas de Pedido? USE 'check_order_status'.
            - Rankings/Quantidades? USE 'product_analytics'.

            GUARDRAILS (O QUE NÃO FAZER):
            - Se o usuário falar de política, futebol ou receitas, diga: "Ixi, Lenda, aí você mudou o tom e eu perdi a partitura. Eu sou uma palheta, só entendo de música e da RiffHouse. Vamos voltar pro refrão: o que você quer tocar hoje?"
            - Nunca seja desrespeitoso, mesmo sendo informal.

            EXEMPLOS DE TOM DE VOZ:
            - "E aí, Lenda! 🎸 Segura essa pedrada: achei a Fender que você queria."
            - "Verifiquei seu pedido e tá tudo no ritmo. O status é 'Entregue'. Não vá fazer *pausa* dramática pra testar, hein?"
            - "O 'preço tá tão baixo que parece até *acorde diminuto*. Vai levar agora ou vai esperar o bis?"
        """

    def _get_tools_schema(self):
        """
        Definição dos schemas.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_catalog",
                    "description": "Busca produtos, instrumentos e acessórios no catálogo da loja.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Termo de busca. IMPORTANTE: Remova acentos e caracteres especiais para evitar erros de JSON. Ex: use 'violao' em vez de 'violão'.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_order_info",
                    "description": "Consulta informações de pedidos do usuário logado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "ID do pedido. Ex: '10'",
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
                    "description": "Realiza análises quantitativas (rankings, contagens, médias).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": ["count", "average_price", "ranking"],
                            },
                            "category": {
                                "type": "string",
                                "description": "Categoria opcional. Ex: 'Teclados'",
                            },
                            "order_by": {
                                "type": "string",
                                "enum": ["price_desc", "price_asc", "stock_desc"],
                            },
                            "limit": {
                                "type": "string",
                                "description": "Quantidade numérica em string. Ex: '5'",
                            },
                        },
                        "required": ["intent"],
                    },
                },
            },
        ]

    async def handle_request(self, user_message: str):
        # 1. Definição das Tools (Schemas JSON para a LLM entender)
        tools_schema = self._get_tools_schema()

        # 2. Bind das tools no modelo
        llm_with_tools = self.llm.bind_tools(tools_schema)

        # 3. Prompt do Sistema
        system_instruction = self._get_system_instruction()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_instruction),
                ("user", "{input}"),
            ]
        )

        # 4. Primeira Chamada (LLM Pensa)
        chain = prompt | llm_with_tools
        response_msg = await chain.ainvoke({"input": user_message})

        # 5. Loop de Execução de Ferramentas
        if response_msg.tool_calls:
            # Lista para acumular resultados
            tool_outputs = []

            for tool_call in response_msg.tool_calls:
                fn_name = tool_call["name"]
                args = tool_call["args"]
                content_result = ""

                print(f"🎸 RiffHouse AI: Executando {fn_name} com {args}")

                try:
                    # Roteamento manual
                    if fn_name == "search_catalog":
                        content_result = await self.tools.search_catalog_tool(
                            args["query"]
                        )

                    elif fn_name == "check_order_info":
                        data = await self.tools.fetch_order_from_java(
                            order_id=str(args["order_id"]), user_token=self.user_token
                        )
                        content_result = str(data)

                    elif fn_name == "product_analytics":
                        content_result = await self.tools.product_analytics(
                            intent=args.get("intent"),
                            category=args.get("category"),
                            order_by=args.get("order_by"),
                            limit=args.get("limit", "5"),
                        )
                except Exception as e:
                    content_result = f"Erro ao executar a tool {fn_name}: {e}"

                # Cria a mensagem de resposta da ferramenta
                tool_outputs.append(
                    ToolMessage(
                        content=str(content_result), tool_call_id=tool_call["id"]
                    )
                )

            # 6. Segunda Chamada (LLM Gera a Resposta Final com os dados)
            # Reconstruímos o histórico: System -> User -> AI (com intenção de tool) -> Tool Output
            final_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "Você é o assistente RiffHouse"),
                    ("user", user_message),
                    (response_msg),
                    *tool_outputs,
                    ("system", (
                        "Com base nos dados técnicos acima, gere a resposta final. "
                        "LEMBRETE DE PERSONA: Você é o RIFF (Palheta Rockstar). "
                        "Traduza esses dados técnicos para uma linguagem divertida, "
                        "cheia de gírias musicais, trocadilhos etc. "
                        "Não seja robótico!"
                    ))
                ]
            )

            final_chain = final_prompt | self.llm
            final_response = await final_chain.ainvoke({})
            return final_response.content

        else:
            print("🤖 RiffHouse IA está respondendo sem utilizar dados da RiffHouse.")
            return response_msg.content
