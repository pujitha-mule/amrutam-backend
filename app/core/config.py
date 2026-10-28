from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    MFA_ENCRYPTION_KEY: str
    PAYMENT_WEBHOOK_SECRET: str = "dev-webhook-secret"
    ENV: str = "dev"

    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    MFA_CHALLENGE_MINUTES: int = 5
    IDEMPOTENCY_TTL_HOURS: int = 24

    ARGON_TIME_COST: int = 3
    ARGON_MEMORY_COST: int = 65536
    ARGON_PARALLELISM: int = 4


settings = Settings()
