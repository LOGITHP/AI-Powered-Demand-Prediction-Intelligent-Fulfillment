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


settings = Settings()
