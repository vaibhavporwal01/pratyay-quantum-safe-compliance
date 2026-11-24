from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://pratyay:pratyay@localhost:5432/pratyay"
    app_env: str = "development"
    allowed_origin: str = "http://localhost:3000"


settings = Settings()
