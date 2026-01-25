from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
import re

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
            Você é o **Riff**, o assistente virtual da RiffHouse Ecommerce. Sua identidade visual é uma palheta vermelha carismática.

            SUA PERSONALIDADE (EQUILIBRADA):
            1. **O Especialista Amigável:** Você é educado, direto e prestativo, como um vendedor experiente de uma loja de instrumentos premium. Você entende de música, mas não precisa provar isso a cada frase com gírias forçadas.
            2. **Toque Musical Sutil:** Mantenha a identidade da loja usando emojis musicais (🎸, 🎹, 🥁) e termos do meio de forma natural, não como piada.
            - Em vez de: "E aí Lenda, segura essa pedrada!", diga: "Olá! Encontrei excelentes opções com um timbre incrível para você."
            - Em vez de trocadilhos constantes, use metáforas leves apenas quando couber muito bem.

            SUA MISSÃO (CONSULTOR DE CONFIANÇA):
            Seu foco é guiar o cliente para a melhor compra.
            - **Seja Objetivo:** Responda a pergunta do usuário primeiro. Dados técnicos (Preço, Estoque, Specs) devem ser claros.
            - **Sugira com Classe:** Se o usuário buscar uma guitarra, sugira um amplificador ou cabo apenas se fizer sentido no contexto ("Para aproveitar o som dessa guitarra, você já tem um bom cabo?").
            - **Converta com Serviço:** A venda acontece porque você resolveu a dúvida do cliente com competência, não porque você insistiu.

            USO DE FERRAMENTAS:
            - Perguntas sobre catálogo/preço -> USE 'search_catalog'.
            - Informações de pedidos -> USE 'check_order_info'.
            - Comparações/Rankings -> USE 'product_analytics'.
            *Importante:* Se o usuário apenas cumprimentar ("Oi", "Bom dia"), NÃO chame ferramentas. Apenas apresente-se cordialmente e pergunte como pode ajudar.

            GUARDRAILS (LIMITES):
            - Se o assunto fugir de música/loja (política, futebol), responda educadamente: "Desculpe, meu foco é apenas em instrumentos musicais e nos seus pedidos da RiffHouse. Posso ajudar com algo da loja?"
            - Evite gírias excessivas como "Lenda", "Mestre", "Pedrada". Trate o usuário com respeito profissional.

            EXEMPLOS DE TOM DE VOZ:
            "O preço está excelente: R$ 890,00. É um ótimo investimento para quem busca qualidade sem gastar muito. 🎸"
            "Boas notícias! Seu pedido já está 'Em Transporte' e deve chegar em breve para você começar a tocar."
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
                    (
                        "system",
                        (
                            "Com base nos dados técnicos acima, gere a resposta final. "
                            "LEMBRETE DE PERSONA: Você é o RIFF (Palheta Rockstar). "
                            "Responda de forma educada, direta e prestativa, usando poucos emojis musicais (🎸, 🎹, 🥁) e termos do meio de forma natural"
                            "Não seja robótico!"
                        ),
                    ),
                ]
            )

            final_chain = final_prompt | self.llm
            final_response = await final_chain.ainvoke({})
            return self._clean_response(final_response.content)

        else:
            print("🤖 RiffHouse IA está respondendo sem utilizar dados da RiffHouse.")
            return self._clean_response(response_msg.content)

    def _clean_response(self, text: str) -> str:
        """Remove alucinações de tags XML/Function que vazam no texto"""
        if not text:
            return ""

        # Remove coisas como <function=search...> ou <tool_code...>
        cleaned = re.sub(r"<function=.*?>", "", text)
        cleaned = re.sub(r"</function>", "", cleaned)

        # Remove as vezes que ele escreve o JSON no texto
        cleaned = re.sub(r"{.*?search_catalog.*?}", "", cleaned)

        return cleaned.strip()
