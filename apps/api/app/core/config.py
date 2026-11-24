from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://pratyay:pratyay@localhost:5432/pratyay"
    app_env: str = "development"
    # Development only: the role used when the pratyay_dev_role cookie is absent.
    dev_user_role: str = "maker"
    allowed_origin: str = "http://localhost:3000"
    # Trained obligation classifier (ml/obligation/train.py). Unset: the repo's ml/ path.
    obligation_model_path: str | None = None


settings = Settings()
