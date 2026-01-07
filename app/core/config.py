from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RiffHouse AI Service"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str 
    
    # AI Providers
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()