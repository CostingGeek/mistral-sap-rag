"""
Application configuration and settings.
"""
import base64
import json
import os
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False
    
    # GCP Configuration
    gcp_project: str = ""
    bq_dataset: str = ""
    bucket_name: str = ""
    
    # GCP Service Account (base64 encoded JSON key)
    gcp_sa_key_base64: Optional[str] = None
    
    # Mistral Configuration
    mistral_api_key: SecretStr
    mistral_base_url: Optional[str] = None
    
    # Model Configuration
    embed_model: str = "mistral-embed"
    chat_model: str = "mistral-medium-latest"
    # Intent classification is a simple routing task; a small model is fast and sufficient
    classify_model: str = "mistral-small-latest"
    
    # Retrieval Configuration
    retrieval_k: int = 8
    
    # Corpus tables (scope selection: standard | nova | both)
    standard_clean_table: str = "doktl_clean"
    standard_embeddings_table: str = "doktl_embeddings"
    nova_clean_table: str = "doktl_nova_clean"
    nova_embeddings_table: str = "doktl_nova_embeddings"
    
# Rate Limiting
    mistral_rate_limit_delay: float = 0.1


# Global settings instance
settings = Settings()


def get_gcp_credentials_dict() -> Optional[dict]:
    """
    Get GCP service account credentials from base64 encoded key.
    Returns None if not configured (will use ADC).
    """
    if not settings.gcp_sa_key_base64:
        return None
    
    try:
        decoded = base64.b64decode(settings.gcp_sa_key_base64).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode GCP service account key: {e}")

