import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Krishna Guidance API"
    environment: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-change-this-secret")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "60"))
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from_email: str | None = os.getenv("SMTP_FROM_EMAIL")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    openai_embedding_dimensions: int = int(
        os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536")
    )
    qdrant_url: str | None = os.getenv("QDRANT_URL")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv(
        "QDRANT_COLLECTION", "bhagavad_gita_sanskrit"
    )
    allowed_origins: list[str] = None

    def __post_init__(self):
        if self.allowed_origins is None:
            object.__setattr__(self, "allowed_origins", ["http://localhost:3000", "http://127.0.0.1:3000"])
        if not self.database_url:
            raise ValueError("DATABASE_URL must be configured.")
        if self.jwt_ttl_minutes <= 0:
            raise ValueError("JWT_TTL_MINUTES must be positive.")
        if self.openai_embedding_dimensions <= 0:
            raise ValueError("OPENAI_EMBEDDING_DIMENSIONS must be positive.")
        if self.environment == "production" and (
            self.jwt_secret
            in {
                "development-only-change-this-secret",
                "replace-with-a-random-secret-of-at-least-32-bytes",
            }
            or len(self.jwt_secret) < 32
        ):
            raise ValueError("JWT_SECRET must contain at least 32 characters in production.")


settings = Settings()
