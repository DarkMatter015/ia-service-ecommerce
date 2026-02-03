from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.ai.agent import get_llm
from app.ai.tools.analytics import AnalyticsTools
from app.ai.tools.catalog import CatalogTools
from app.ai.tools.orders import OrdersTools

from app.ai.prompts import (
    get_system_instruction,
    get_tools_schema,
    get_final_response_prompt,
)

import logging

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, db: AsyncSession, user_token: str):
        self.db = db
        self.llm = get_llm()
        self.user_token = user_token
        self.analytics_tools = AnalyticsTools(db)
        self.catalog_tools = CatalogTools(db)
        self.orders_tools = OrdersTools(db)

    async def handle_request(self, user_message: str):
        # 1. Definição das Tools (Schemas JSON para a LLM entender)
        tools_schema = get_tools_schema()

        # 2. Bind das tools no modelo
        llm_with_tools = self.llm.bind_tools(tools_schema)

        # 3. Prompt do Sistema
        system_instruction = get_system_instruction()

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

                logger.info(f"🎸 RiffHouse AI: Executando {fn_name} com {args}")

                try:
                    # Roteamento manual
                    if fn_name == "search_catalog":
                        content_result = await self.catalog_tools.search_catalog_tool(
                            args["query"]
                        )

                    elif fn_name == "check_order_info":
                        data = await self.orders_tools.fetch_order_from_java(
                            order_id=str(args["order_id"]), user_token=self.user_token
                        )
                        content_result = str(data)

                    elif fn_name == "product_analytics":
                        content_result = await self.analytics_tools.product_analytics(
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
                    ("system", get_final_response_prompt()),
                ]
            )

            final_chain = final_prompt | self.llm
            final_response = await final_chain.ainvoke({})
            return self._clean_response(final_response.content)

        else:
            logger.info(
                "🤖 RiffHouse IA está respondendo sem utilizar dados da RiffHouse."
            )
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
