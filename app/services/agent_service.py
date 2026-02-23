import logging
import re

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import get_llm
from app.ai.prompts import (
    get_final_response_prompt,
    get_system_instruction,
    get_tools_schema,
)
from app.ai.tools.analytics import AnalyticsTools
from app.ai.tools.catalog import CatalogTools
from app.ai.tools.orders import OrdersTools
from app.schemas.chat_schema import ChatResponse
from app.services.chat_service import ChatService
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, db: AsyncSession, user_token: str):
        self.db = db
        self.llm = get_llm()
        self.user_token = user_token
        self.analytics_tools = AnalyticsTools(db)
        self.catalog_tools = CatalogTools(db)
        self.orders_tools = OrdersTools(db)
        self.chat_service = ChatService(db, user_token)
        self.security_service = SecurityService()

    async def handle_request(self, user_message: str, session_id: str) -> ChatResponse:
        # 1. Definição das Tools (Schemas JSON para a LLM entender)
        tools_schema = get_tools_schema()
        # 2. Bind das tools no modelo
        llm_with_tools = self.llm.bind_tools(tools_schema)
        # 3. Prompt do Sistema
        system_instruction = get_system_instruction()

        token = self.security_service.validar_jwt(self.user_token)
        user_id = token.get("sub") if token else None
        is_anonymous = user_id is None

        context = []

        if not session_id:
            logger.info("Nenhum session_id fornecido. Inicializando nova sessão.")
            if not is_anonymous:
                session = await self.chat_service.create_session(
                    user_id=user_id, title=user_message[:20]
                )  # Título inicial é os primeiros 20 chars da mensagem
                session_id = session.id
                logger.info(f"Nova sessão criada: {session}")
            else:
                import uuid

                session_id = str(uuid.uuid4())  # ID efêmero apenas para o Redis
                logger.info(f"Sessão efêmera criada: {session_id}")
        else:
            # Apenas busca no banco se não for anônimo, mas sempre busca no Redis
            if not is_anonymous:
                session = await self.chat_service.get_session(session_id)
            context = await self.chat_service.get_context(session_id)
            logger.info(
                f"Contexto carregado. {len(context)} interações. Session ID: {session_id}"
            )

        # 4. Primeira Chamada (LLM Pensa)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_instruction),
                *context,
                ("user", "{input}"),
            ]
        )

        chain = prompt | llm_with_tools
        response_msg = await chain.ainvoke({"input": user_message})

        # 5. Loop de Execução de Ferramentas
        if response_msg.tool_calls:
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
                    logger.error("🔥 ERRO CRÍTICO NA INGESTÃO", exc_info=True)
                    content_result = f"Erro ao executar a tool {fn_name}: {e}"

                # Cria a mensagem de resposta da ferramenta
                tool_outputs.append(
                    ToolMessage(
                        content=str(content_result), tool_call_id=tool_call["id"]
                    )
                )

            # 6. Segunda Chamada (LLM Gera a Resposta Final com os dados)
            final_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "Você é o assistente RiffHouse, especializado em responder perguntas sobre produtos e pedidos da loja de e-commerce RiffHouse.",
                    ),
                    *context,  # Contexto passado
                    ("user", user_message),  # Pergunta atual
                    response_msg,  # Intenção da Tool
                    *tool_outputs,  # Dados brutos retornados
                    ("system", get_final_response_prompt()),
                ]
            )

            final_chain = final_prompt | self.llm
            final_content = await final_chain.ainvoke({})
        else:
            logger.info(
                "🤖 RiffHouse IA está respondendo sem utilizar dados da RiffHouse."
            )
            final_content = response_msg.content

        # 7. Persistência do diálogo (somente se não for anônimo, para evitar poluir o banco com sessões efêmeras)
        if not is_anonymous:
            await self.chat_service.save_message(session_id, "user", user_message)
            await self.chat_service.save_message(session_id, "assistant", final_content)
        else:
            await self.chat_service.save_context_only(session_id, "user", user_message)
            await self.chat_service.save_context_only(session_id, "assistant", final_content)

        # Alterado para retornar session_id explícito, evitando conflitos com `session=None`
        return ChatResponse(
            response=self._clean_response(final_content), 
            session_id=session_id 
        )

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
