from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FulfillIQ"
    DATABASE_URL: str = "sqlite+aiosqlite:///./fulfilliq.db"
    JWT_SECRET: str = "fulfilliq-local-development-secret-change-before-deployment"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    MODEL_STORAGE_PATH: str = "./ml_models"
    SEED: int = 42
    HISTORICAL_ORDER_COUNT: int = 30000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        # Render provides PostgreSQL URLs with the generic scheme, while this
        # application uses SQLAlchemy's async engine and asyncpg driver.
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL


settings = Settings()
