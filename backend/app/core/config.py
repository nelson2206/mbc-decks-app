"""Application configuration loaded from environment variables."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    app_name: str = "MBC Decks"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Anthropic API (key compartida MBC)
    anthropic_api_key: str = Field(default="", description="Set ANTHROPIC_API_KEY env var")
    anthropic_model_main: str = "claude-sonnet-4-6"
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"

    # Database
    database_url: str = "postgresql+psycopg2://mbcdecks:mbcdecks@localhost:5432/mbcdecks"

    # Storage (S3/R2 o filesystem local)
    storage_backend: str = "local"  # "local" o "s3"
    storage_local_path: Path = Path("/tmp/mbcdecks_storage")
    s3_bucket: str = ""
    s3_region: str = "auto"  # auto para Cloudflare R2
    s3_endpoint_url: str = ""  # https://<account>.r2.cloudflarestorage.com para R2
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Auth
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 8

    # Plugin resources (paths a los archivos del skill)
    plugin_path: Path = Path(__file__).parent.parent / "plugin_resources"

    @property
    def template_path(self) -> Path:
        return self.plugin_path / "assets" / "template" / "PPT_MINSAIT_Template_esp.potx"

    @property
    def archetypes_path(self) -> Path:
        return self.plugin_path / "skills" / "generate-deck" / "archetypes"

    @property
    def brand_path(self) -> Path:
        return self.plugin_path / "skills" / "generate-deck" / "brand"

    @property
    def knowledge_path(self) -> Path:
        return self.plugin_path / "skills" / "generate-deck" / "knowledge"

    @property
    def prompts_path(self) -> Path:
        return self.plugin_path / "skills" / "generate-deck" / "prompts"

    @property
    def credenciales_path(self) -> Path:
        return self.plugin_path / "credenciales"


settings = Settings()
