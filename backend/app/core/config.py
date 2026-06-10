import os
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# El fichero .env a cargar es configurable vía la variable de entorno ENV_FILE.
# En producción/desarrollo se usa el ".env" por defecto; la suite de tests lo
# apunta a una ruta inexistente para garantizar un entorno determinista
# (independiente de cualquier .env presente en disco).
_ENV_FILE = os.environ.get("ENV_FILE", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_ORIGIN: AnyHttpUrl
    COOKIES_SECURE: bool = True
    RIOT_API_KEY: str | None = None
    # M-06: hosts de los que se confía el header X-Forwarded-For para el
    # rate-limit por IP. Por defecto sólo loopback (NUNCA "*", que permitiría
    # spoofear la IP). En producción tras un proxy, fijar la IP/red del proxy.
    FORWARDED_ALLOW_IPS: str = "127.0.0.1"
    # P2/I-01: en producción se desactivan los docs públicos (/docs, /redoc,
    # /openapi.json). Controla también cabeceras dependientes de entorno.
    ENVIRONMENT: str = "development"

    @field_validator("RIOT_API_KEY", mode="before")
    @classmethod
    def _empty_riot_key_is_none(cls, v):
        """Normaliza la key: cadena vacía o solo espacios/comillas → None.

        Compose/env_file pueden entregar `RIOT_API_KEY=""` (cadena vacía) en
        vez de no definirla. Sin esto, la factoría construiría
        HttpRiotAPIClient con una key vacía y Riot devolvería 401. También
        recortamos espacios y comillas accidentales del .env.
        """
        if v is None:
            return None
        stripped = v.strip().strip('"').strip("'").strip()
        return stripped or None


@lru_cache
def get_settings() -> Settings:
    """Settings cacheadas (L-07): se construyen una sola vez por proceso.

    En tests que muten el entorno de settings, invalidar con
    `get_settings.cache_clear()`. La suite fija el entorno una vez en
    `tests/conftest.py` antes del primer acceso, por lo que la caché es segura.
    """
    return Settings()
