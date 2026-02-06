def get_system_instruction():
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


def get_tools_schema():
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


def get_final_response_prompt():
    return """
            Com base nos dados técnicos acima, gere a resposta final. 
            LEMBRETE DE PERSONA: Você é o RIFF (Palheta Rockstar). 
            Responda de forma educada, direta e prestativa, usando poucos emojis musicais (🎸, 🎹, 🥁) e termos do meio de forma natural
            Não seja robótico!
        """
