from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Phone = Annotated[str, Field(pattern=r"^\+[1-9][0-9]{6,14}$")]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr | None = None
    secure_cookies: bool = False
    server_public_url: str = "http://localhost:8000"
    emergency_sms_gateway_number: Phone | None = None
    android_sms_gateway_webhook_secret: SecretStr | None = None
    android_sms_gateway_url: str | None = None
    android_sms_gateway_user: str | None = None
    android_sms_gateway_password: SecretStr | None = None
    session_seconds: int = Field(default=28800, ge=60, le=86400)

    @field_validator("server_public_url")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        from urllib.parse import urlsplit

        url = urlsplit(value)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
            or value != value.strip()
        ):
            raise ValueError("Expected an HTTP(S) origin")
        if url.scheme == "http" and url.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Plain HTTP is allowed only on loopback")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_cookie_configuration(self):
        if self.secure_cookies is False and not self.server_public_url.startswith(
            "http://"
        ):
            raise ValueError(
                "Insecure cookies require an explicitly configured loopback HTTP origin"
            )
        return self

    def postgres_url(self) -> str:
        url = self.database_url.get_secret_value() if self.database_url else ""
        if url.startswith("postgresql://"):
            try:
                import pg8000
                return url.replace("postgresql://", "postgresql+pg8000://", 1)
            except ImportError:
                return url
        if url.startswith("postgresql+") or url.startswith("sqlite"):
            return url
        # Default local embedded database fallback so the app runs immediately
        return "sqlite:///disasterops.db"
