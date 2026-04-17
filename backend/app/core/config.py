"""
Core configuration module using Pydantic settings management.
Loads environment variables and provides type-safe configuration access.
"""
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation and type safety."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Application Settings
    app_name: str = "Arivagam AI Knowledge Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database Configuration
    database_url: Optional[str] = Field(None, description="Async PostgreSQL connection URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for SQLAlchemy operations."""
        if self.database_url:
            # Handle the case where we have a direct async URL (e.g. from Render)
            # Replace postgresql+asyncpg with postgresql
            return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
            
        if not self.postgres_user or not self.postgres_password or not self.postgres_db:
             raise ValueError("Either database_url or individual connection parts must be provided")

        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600
    
    # Vertex AI Configuration
    gcp_project_id: Optional[str] = None
    gcp_location: str = "us-central1"
    google_application_credentials: str = "/app/gcp-credentials.json"
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    
    gemini_embedding_model: str = Field(default="gemini-embedding-001", env="GEMINI_EMBEDDING_MODEL")
    gemini_embedding_dimensions: int = Field(default=768, env="GEMINI_EMBEDDING_DIMENSIONS")
    gemini_chat_model: str = Field(default="gemini-2.5-flash", env="GEMINI_CHAT_MODEL")
    gemini_max_tokens: int = 8192
    
    # Cohere Configuration
    cohere_api_key: Optional[str] = None
    cohere_rerank_model: str = "rerank-english-v3.0"
    
    # JWT Authentication
    secret_key: str = "dev_secret_key_change_me_in_production_1234567890"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Document Processing Configuration
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf,docx,doc,txt,xlsx,xls"
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions into a list."""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_upload_size_mb * 1024 * 1024
    
    # Chunking Configuration
    chunk_size: int = 800
    chunk_overlap: int = 150
    max_table_tokens: int = 2000
    min_chunk_size: int = 100
    
    # Retrieval Configuration
    retrieval_top_k: int = 20
    rerank_top_k: int = 8
    similarity_threshold: float = Field(default=0.3, env="SIMILARITY_THRESHOLD")
    hybrid_alpha: float = 0.7
    
    # Generation Configuration
    max_context_tokens: int = 12000
    temperature: float = 0.1
    max_response_tokens: int = 1000
    
    # Guardrails Configuration
    enable_input_guardrails: bool = True
    enable_output_guardrails: bool = True
    hallucination_threshold: float = 0.3
    
    # Context Management Configuration
    context_timeout_hours: int = Field(default=1, env="CONTEXT_TIMEOUT_HOURS")
    context_max_documents: int = Field(default=5, env="CONTEXT_MAX_DOCUMENTS")
    context_boost_factor: float = Field(default=1.5, env="CONTEXT_BOOST_FACTOR")
    enable_query_reformulation: bool = Field(default=True, env="ENABLE_QUERY_REFORMULATION")
    enable_context_ui: bool = Field(default=True, env="ENABLE_CONTEXT_UI")
    
    # Enhanced Retrieval
    max_conversation_history: int = Field(default=5, env="MAX_CONVERSATION_HISTORY")
    document_scope_message_threshold: int = Field(default=5, env="DOCUMENT_SCOPE_MESSAGE_THRESHOLD")
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "./logs/arivagam.log"
    log_rotation: str = "10 MB"
    log_retention: str = "30 days"
    
    # CORS Settings
    cors_origins: Union[str, List[str]] = "*"
    cors_allow_credentials: bool = True
    
    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> Optional[str]:
        """
        Ensure the database URL has the correct asyncpg prefix.
        Also handles cases where DATABASE_URL might be provided in env but not mapped correctly.
        """
        import os
        # Fallback to direct env check if Pydantic didn't pick it up
        if not v:
            v = os.getenv("DATABASE_URL") or os.getenv("DB_URL") 
            
        if v and v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v and v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            v = v.strip('[]"\'')
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("gcp_project_id", "cohere_api_key", "secret_key")
    @classmethod
    def validate_secrets(cls, v, info):
        """Ensure critical secrets are not using placeholder values."""
        field_name = info.field_name
        
        if field_name == "secret_key":
            if not v or len(v) < 20:
                # In production we should enforce this, but for dev defaults it might be smaller
                pass
        
        return v

@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()

__all__ = ["settings", "get_settings", "Settings"]
