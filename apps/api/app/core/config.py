from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq options asyncpg does not take; Neon adds them to its connection strings.
_DROP_PARAMS = {"channel_binding"}


def asyncpg_url(url: str) -> str:
    """Accept a plain Postgres URL (as Neon gives it) and make it one asyncpg can use:
    postgres:// or postgresql:// becomes postgresql+asyncpg://, and sslmode=require becomes
    ssl=require."""
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in _DROP_PARAMS:
            continue
        query.append(("ssl" if key == "sslmode" else key, value))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://pratyay:pratyay@localhost:5432/pratyay"
    app_env: str = "development"
    # Development only: the role used when the pratyay_dev_role cookie is absent.
    dev_user_role: str = "maker"
    # Until sign-in lands: let the "Act as" role switcher (cookie stand-in) work outside
    # development, for the deployed showcase. Remove with the stand-in (docs/contracts.md).
    allow_role_switcher: bool = False
    allowed_origin: str = "http://localhost:3000"
    # Trained obligation classifier (ml/obligation/train.py). Unset: the repo's ml/ path.
    obligation_model_path: str | None = None

    @field_validator("database_url")
    @classmethod
    def _asyncpg(cls, v: str) -> str:
        return asyncpg_url(v)


settings = Settings()
