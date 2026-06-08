from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_ORIGIN: AnyHttpUrl
    COOKIES_SECURE: bool = True
    RIOT_API_KEY: str | None = None

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


def get_settings() -> Settings:
    return Settings()
