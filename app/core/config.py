import logging
import sys
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RiffHouse AI Service"
    API_V1_STR: str = "/api/v1"

    # Define o ambiente: 'local', 'staging' ou 'production'
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Nível de Log: DEBUG para local, INFO para produção
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Database ---
    DB_HOST: str | None = None
    DB_PORT: str | None = "5432"
    DB_NAME: str | None = None
    DB_USERNAME: str | None = None
    DB_PASSWORD: str | None = None

    # Caso queira passar a URL completa direto
    DATABASE_URL: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Monta a URL de conexão Async do SQLAlchemy.
        Prioridade: DATABASE_URL > Componentes individuais.
        """
        if self.DATABASE_URL:
            # Garante o driver async (asyncpg) mesmo se a env var vier como 'postgresql://'
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        if self.DB_HOST and self.DB_NAME and self.DB_USERNAME and self.DB_PASSWORD:
            return (
                f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )

        # Retorna uma string vazia ou erro se faltar config,
        raise ValueError(
            "Configuração de Banco incompleta! Defina DATABASE_URL ou as variáveis DB_..."
        )

    # --- AI Providers ---
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    # --- Integrações ---
    BACKEND_URL: str = "http://localhost:8080"
    JWT_SECRET: str

    # --- RabbitMq ---
    RABBITMQ_HOST: str | None = None
    RABBITMQ_PORT: str | None = "5672"
    RABBITMQ_VHOST: str | None = None
    RABBITMQ_USERNAME: str | None = None
    RABBITMQ_PASSWORD: str | None = None

    # Caso queira passar a URL completa direto
    RABBITMQ_URL: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def GET_RABBITMQ_URL(self) -> str:
        """
        Monta a URL de conexão do Rabbitmq.
        Prioridade: RABBITMQ_URL > Componentes individuais.
        """
        if self.RABBITMQ_URL:
            return self.RABBITMQ_URL

        if (
            self.RABBITMQ_HOST
            and self.RABBITMQ_USERNAME
            and self.RABBITMQ_VHOST
            and self.RABBITMQ_PASSWORD
        ):
            return (
                f"amqp://{self.RABBITMQ_USERNAME}:{self.RABBITMQ_PASSWORD}"
                f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
            )

        # Retorna uma string vazia ou erro se faltar config,
        raise ValueError(
            "Configuração de Rabbitmq incompleta! Defina RABBITMQ_URL ou as variáveis RABBITMQ_..."
        )

    # --- Redis ---
    REDIS_HOST: str | None = None
    REDIS_PORT: str | None = "6379"
    REDIS_DB: str | None = "0"

    # Caso queira passar a URL completa direto
    REDIS_URL: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def GET_REDIS_URL(self) -> str:
        """
        Monta a URL de conexão do Redis.
        Prioridade: REDIS_URL > Componentes individuais.
        """
        if self.REDIS_URL:
            return self.REDIS_URL

        if self.REDIS_HOST and self.REDIS_DB:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

        # Retorna uma string vazia ou erro se faltar config,
        raise ValueError(
            "Configuração de Redis incompleta! Defina REDIS_URL ou as variáveis REDIS_..."
        )

    # --- Configuração do Pydantic v2 ---
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGGING
# ---------------------------------------------------------------------------
def setup_logging(settings: Settings):
    """
    Configura o logger globalmente usando dictConfig.
    """

    # Formato dos logs: Timestamp | Nível | Logger | Mensagem
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            }
            if settings.ENVIRONMENT == "production"
            else {"format": log_format},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
                "level": settings.LOG_LEVEL,
            },
        },
        "loggers": {
            # Logger Raiz (Pega tudo)
            "": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
            },
            # Logger da sua Aplicação (app.*)
            "app": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            # SQLAlchemy: Mostra SQL no console apenas se for DEBUG
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "INFO" if settings.LOG_LEVEL == "DEBUG" else "WARNING",
                "propagate": False,
            },
            # RabbitMQ Lib (aio_pika)
            "aio_pika": {
                "handlers": ["console"],
                "level": "WARNING",  # Evita spam de heartbeat
                "propagate": False,
            },
            # Uvicorn (Servidor Web)
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


settings = Settings()

setup_logging(settings)
