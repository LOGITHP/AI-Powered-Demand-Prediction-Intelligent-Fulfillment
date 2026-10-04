import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Operations System"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://warehouse_user:warehouse_password@localhost:5432/warehouse")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-" + "x" * 40)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama3-70b-instruct")
    HEAD_OFFICE_BASE_URL: str = os.getenv("HEAD_OFFICE_BASE_URL", "http://localhost:8001")
    WAREHOUSE_ID: str = os.getenv("WAREHOUSE_ID", "WH-001")
    
    ML_MODELS_PATH: str = os.getenv("ML_MODELS_PATH", "/app/models")

settings = Settings()

