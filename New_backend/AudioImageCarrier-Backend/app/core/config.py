"""Configuration management for AudioImageCarrier API."""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="AudioImageCarrier API")
    app_version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="production")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # Security - API Key
    api_key: str = Field(default="dev-test-key-12345")
    
    # File Storage
    upload_dir: str = Field(default=os.environ.get("UPLOAD_DIR", "/tmp/uploads" if os.environ.get("VERCEL") else "storage/uploads"))
    temp_dir: str = Field(default=os.environ.get("TEMP_DIR", "/tmp" if os.environ.get("VERCEL") else "storage/temp"))
    max_upload_size_mb: int = Field(default=500)
    
    # Audio Processing
    default_max_chunk_bytes: int = Field(default=52428800)  # 50MB
    max_width: int = Field(default=8192)
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    cors_allow_credentials: bool = Field(default=True)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency function to get settings instance."""
    return settings