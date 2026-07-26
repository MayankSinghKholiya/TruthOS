"""Central application settings, loaded from environment variables only."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_secret_key: str = Field(alias="APP_SECRET_KEY")
    app_allowed_origins: str = Field(default="http://localhost:3000", alias="APP_ALLOWED_ORIGINS")

    # Auth
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Postgres
    database_url: str = Field(alias="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="", alias="NEO4J_PASSWORD")

    # LLM routing
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    default_model: str = Field(default="anthropic/claude-sonnet-4.5", alias="DEFAULT_MODEL")
    fallback_model: str = Field(default="openai/gpt-4o-mini", alias="FALLBACK_MODEL")
    judge_model: str = Field(default="anthropic/claude-opus-4.1", alias="JUDGE_MODEL")

    # External APIs
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    coingecko_api_key: str = Field(default="", alias="COINGECKO_API_KEY")
    alphavantage_api_key: str = Field(default="", alias="ALPHAVANTAGE_API_KEY")

    # On-chain evidence verification (TruthOS Court)
    # Optional "chain=url,chain=url" overrides for the built-in public RPC
    # defaults in app.services.chain_verification - lets a stale free
    # endpoint be swapped without a code change.
    chain_rpc_urls: str = Field(default="", alias="CHAIN_RPC_URLS")

    # Telegram notifications - empty token disables the feature entirely
    # (linking endpoints 503, the notify helper no-ops) rather than crashing
    # a deployment that hasn't set one up yet.
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    # Storage
    r2_account_id: str = Field(default="", alias="R2_ACCOUNT_ID")
    r2_access_key_id: str = Field(default="", alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field(default="", alias="R2_SECRET_ACCESS_KEY")
    r2_bucket_name: str = Field(default="truthos-storage", alias="R2_BUCKET_NAME")

    # Observability
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")
    posthog_api_key: str = Field(default="", alias="POSTHOG_API_KEY")
    posthog_host: str = Field(default="https://app.posthog.com", alias="POSTHOG_HOST")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
