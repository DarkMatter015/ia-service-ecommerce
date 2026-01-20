from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "RiffHouse AI Service"
    API_V1_STR: str = "/api/v1"

    # Database
    DB_HOST: str | None = None
    DB_PORT: str | None = None
    DB_NAME: str | None = None
    DB_USERNAME: str | None = None
    DB_PASSWORD: str | None = None
    DATABASE_URL: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        if (
            self.DB_HOST
            and self.DB_PORT
            and self.DB_NAME
            and self.DB_USERNAME
            and self.DB_PASSWORD
        ):
            return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

        raise ValueError(
            "Database configuration is incomplete. define DATABASE_URL or (DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD)."
        )

    # AI Providers
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    # BACKEND
    BACKEND_URL: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()