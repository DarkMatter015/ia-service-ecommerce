import json
import aio_pika
import logging
from aio_pika.abc import AbstractIncomingMessage
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.product_sync_service import ProductSyncService

logger = logging.getLogger(__name__)

# --- CONSTANTES DE NOMENCLATURA (Hardcoded ou via .env) ---
# Main (Onde o Java manda)
MAIN_EXCHANGE_NAME = "products.topic"
MAIN_QUEUE_NAME = "ai.product.sync.queue"
ROUTING_KEYS = ["product.created", "product.updated"]

# Dead Letter (Infra de Erro)
DLX_EXCHANGE_NAME = "products.dlx"       # Exchange dos Mortos
DLQ_QUEUE_NAME = "ai.product.sync.dlq"   # Fila dos Mortos
DLQ_ROUTING_KEY = "dead.letter"          # Chave de roteamento para erro


async def process_message(message: AbstractIncomingMessage):
    async with message.process(ignore_processed=True):
        try:
            body = message.body.decode()
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                logger.error("JSON Inválido. Enviando para DLQ.")
                await message.nack(requeue=False) # Vai para DLQ
                return

            logger.info(f"Recebido: {data.get('id', '?')} | Evento: {message.routing_key}")

            async with SessionLocal() as db:
                service = ProductSyncService(db)
                await service.upsert_product(data)
                
            logger.info(f"✅ Sucesso: {data.get('id')}")

        except Exception as e:
            logger.error(f"❌ Erro processando msg: {e}", exc_info=True)
            # Requeue=False manda para a DLQ configurada na fila principal
            await message.nack(requeue=False)

async def start_rabbitmq_consumer():
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # ==================================================================
        # 1. CRIAR INFRAESTRUTURA DE DEAD LETTER (DLQ)
        # ==================================================================
        
        # Exchange para erros (Direct)
        dlx = await channel.declare_exchange(
            DLX_EXCHANGE_NAME, 
            aio_pika.ExchangeType.DIRECT, 
            durable=True
        )

        # Fila de erros
        dlq = await channel.declare_queue(DLQ_QUEUE_NAME, durable=True)

        # Liga a fila DLQ ao Exchange DLX
        await dlq.bind(dlx, routing_key=DLQ_ROUTING_KEY)


        # ==================================================================
        # 2. CRIAR INFRAESTRUTURA PRINCIPAL (MAIN)
        # ==================================================================

        # Exchange Principal (Topic - Para permitir filtros flexíveis)
        main_exchange = await channel.declare_exchange(
            MAIN_EXCHANGE_NAME, 
            aio_pika.ExchangeType.TOPIC, 
            durable=True
        )

        # Fila Principal (Com configuração para jogar erros no DLX)
        main_queue = await channel.declare_queue(
            MAIN_QUEUE_NAME, 
            durable=True,
            arguments={
                # Se der Nack(False), jogue para cá:
                "x-dead-letter-exchange": DLX_EXCHANGE_NAME,
                # Com esta etiqueta:
                "x-dead-letter-routing-key": DLQ_ROUTING_KEY
            }
        )

        # Bind: Liga as chaves que o Java envia à fila do Python
        for key in ROUTING_KEYS:
            await main_queue.bind(main_exchange, routing_key=key)

        logger.info(f"Consumer ouvindo '{MAIN_QUEUE_NAME}' no exchange '{MAIN_EXCHANGE_NAME}'")
        
        await main_queue.consume(process_message)
        return connection

    except Exception as e:
        logger.critical(f"Erro fatal RabbitMQ: {e}")
        raise e