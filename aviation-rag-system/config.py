"""
Central configuration module for Aviation RAG System.

This module loads all configuration from environment variables and provides
a centralized configuration object for the entire application.

Usage:
    from config import config

    # Access configuration
    qdrant_host = config.QDRANT_HOST
    model_name = config.EMBEDDING_MODEL
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ========================================
    # API Security
    # ========================================
    API_KEY: str = Field(..., description="Secret API key for authentication")
    CORS_ORIGINS: str = Field(
        "http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )
    RATE_LIMIT: int = Field(100, description="Rate limit (requests per minute)")

    # ========================================
    # Qdrant Configuration
    # ========================================
    QDRANT_HOST: str = Field("localhost", description="Qdrant host")
    QDRANT_PORT: int = Field(6333, description="Qdrant port")
    QDRANT_COLLECTION_NAME: str = Field(
        "aviation_regulations",
        description="Qdrant collection name"
    )
    QDRANT_API_KEY: Optional[str] = Field(None, description="Qdrant Cloud API key")

    # ========================================
    # Ollama Configuration
    # ========================================
    OLLAMA_HOST: str = Field(
        "http://localhost:11434",
        description="Ollama server URL"
    )
    OLLAMA_MODEL: str = Field("llama3.1:8b", description="Ollama model name")

    # LLM parameters
    LLM_TEMPERATURE: float = Field(0.3, description="LLM temperature (0-1)")
    LLM_TOP_P: float = Field(0.9, description="LLM top-p sampling")
    LLM_MAX_TOKENS: int = Field(500, description="Maximum tokens in LLM response")

    # ========================================
    # Embedding Model
    # ========================================
    EMBEDDING_MODEL: str = Field(
        "rufimelo/Legal-BERTimbau-sts-large-ma-v3",
        description="HuggingFace embedding model name"
    )
    EMBEDDING_BATCH_SIZE: int = Field(32, description="Batch size for embeddings")
    EMBEDDING_MAX_LENGTH: int = Field(512, description="Max sequence length")
    EMBEDDING_DIMENSION: int = Field(1024, description="Embedding vector dimension")

    # ========================================
    # Search Configuration
    # ========================================
    SEARCH_TOP_K: int = Field(5, description="Number of top results to return")
    SEARCH_SCORE_THRESHOLD: float = Field(
        0.7,
        description="Minimum similarity score (0-1)"
    )
    HNSW_EF_SEARCH: int = Field(64, description="HNSW ef parameter for search")
    HNSW_M: int = Field(16, description="HNSW M parameter (connections per node)")
    HNSW_EF_CONSTRUCT: int = Field(100, description="HNSW ef_construct parameter")

    # ========================================
    # Chunking Configuration
    # ========================================
    CHUNK_MAX_TOKENS: int = Field(512, description="Maximum tokens per chunk")
    CHUNK_OVERLAP: int = Field(50, description="Overlap between chunks (tokens)")

    # ========================================
    # Temporal Extraction
    # ========================================
    DEFAULT_EFFECTIVE_DAYS: int = Field(
        90,
        description="Default days to add to publication date if no effective date found"
    )

    # ========================================
    # LexML Scraper Configuration
    # ========================================
    LEXML_API_URL: str = Field(
        "https://www.lexml.gov.br/sru",
        description="LexML SRU API URL"
    )
    LEXML_MAX_RECORDS_PER_PAGE: int = Field(
        100,
        description="Maximum records per page in LexML API"
    )
    LEXML_KEYWORDS: str = Field(
        "aviação,aeronave,ANAC,voo,tripulação,piloto,aeroporto",
        description="Comma-separated keywords for aviation documents"
    )

    # ========================================
    # PDF Parser Configuration
    # ========================================
    ENABLE_OCR: bool = Field(False, description="Enable OCR for scanned PDFs")
    OCR_LANGUAGE: str = Field("por", description="OCR language code")

    # ========================================
    # Logging
    # ========================================
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FILE: str = Field("logs/aviation-rag.log", description="Log file path")
    LOG_ROTATION: str = Field("500 MB", description="Log rotation size")
    LOG_RETENTION: str = Field("30 days", description="Log retention period")

    # ========================================
    # Cache Configuration (Optional)
    # ========================================
    REDIS_HOST: Optional[str] = Field(None, description="Redis host")
    REDIS_PORT: int = Field(6379, description="Redis port")
    REDIS_DB: int = Field(0, description="Redis database number")
    CACHE_TTL: int = Field(3600, description="Cache TTL in seconds")

    # ========================================
    # Database Configuration (Optional)
    # ========================================
    DATABASE_URL: Optional[str] = Field(
        None,
        description="PostgreSQL database URL for metadata storage"
    )

    # ========================================
    # Monitoring (Optional)
    # ========================================
    ENABLE_METRICS: bool = Field(False, description="Enable Prometheus metrics")
    PROMETHEUS_PORT: int = Field(9091, description="Prometheus exporter port")

    # ========================================
    # Development Settings
    # ========================================
    ENVIRONMENT: str = Field("development", description="Environment: development | production")
    DEBUG: bool = Field(True, description="Debug mode")
    RELOAD: bool = Field(True, description="Reload on code changes")

    # ========================================
    # Performance Tuning
    # ========================================
    API_WORKERS: int = Field(4, description="Number of API workers (production)")
    CUDA_VISIBLE_DEVICES: str = Field(
        "0,1,2,3,4,5",
        description="Comma-separated GPU device IDs"
    )

    # ========================================
    # Data Paths
    # ========================================
    DATA_DIR: str = Field("./data", description="Path to store downloaded documents")
    PROCESSED_DIR: str = Field(
        "./data/processed",
        description="Path to store processed documents"
    )
    MODEL_CACHE_DIR: str = Field(
        "./models_cache",
        description="Path to store model cache"
    )

    # ========================================
    # API Configuration
    # ========================================
    API_HOST: str = Field("0.0.0.0", description="API host")
    API_PORT: int = Field(8000, description="API port")
    API_TITLE: str = Field("Aviation RAG API", description="API title")
    API_VERSION: str = Field("1.0.0", description="API version")
    API_DESCRIPTION: str = Field(
        "Retrieval-Augmented Generation API for Brazilian Aviation Regulations",
        description="API description"
    )

    # ========================================
    # Ingestion Configuration
    # ========================================
    INGESTION_BATCH_SIZE: int = Field(
        100,
        description="Number of documents to process in batch"
    )
    ENABLE_PARALLEL_PROCESSING: bool = Field(
        True,
        description="Enable parallel processing"
    )
    NUM_WORKERS: int = Field(4, description="Number of parallel workers")

    # ========================================
    # Advanced Settings
    # ========================================
    LOG_QUERIES: bool = Field(True, description="Enable query logging")
    ENABLE_PROFILING: bool = Field(False, description="Enable performance profiling")
    LLM_TIMEOUT: int = Field(60, description="Timeout for LLM requests (seconds)")
    SEARCH_TIMEOUT: int = Field(10, description="Timeout for vector search (seconds)")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    # ========================================
    # Derived Properties
    # ========================================
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def lexml_keywords_list(self) -> List[str]:
        """Parse LexML keywords from comma-separated string."""
        return [kw.strip() for kw in self.LEXML_KEYWORDS.split(",")]

    @property
    def cuda_devices_list(self) -> List[int]:
        """Parse CUDA device IDs from comma-separated string."""
        if not self.CUDA_VISIBLE_DEVICES:
            return []
        try:
            return [int(d.strip()) for d in self.CUDA_VISIBLE_DEVICES.split(",")]
        except ValueError:
            return []

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    # ========================================
    # Path Helpers
    # ========================================
    def get_data_path(self, filename: str = "") -> Path:
        """Get path in data directory."""
        path = Path(self.DATA_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path / filename if filename else path

    def get_processed_path(self, filename: str = "") -> Path:
        """Get path in processed directory."""
        path = Path(self.PROCESSED_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path / filename if filename else path

    def get_model_cache_path(self, filename: str = "") -> Path:
        """Get path in model cache directory."""
        path = Path(self.MODEL_CACHE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path / filename if filename else path

    def get_log_path(self) -> Path:
        """Get log file path."""
        log_path = Path(self.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path


# ========================================
# Global Configuration Instance
# ========================================
try:
    config = Settings()
except Exception as e:
    # If .env file doesn't exist or has errors, provide helpful message
    print(f"Error loading configuration: {e}")
    print("\nPlease ensure:")
    print("1. You have copied .env.example to .env")
    print("2. All required environment variables are set in .env")
    print("3. The .env file is in the project root directory")
    raise


# ========================================
# Configuration Validation
# ========================================
def validate_config() -> bool:
    """
    Validate configuration settings.

    Returns:
        bool: True if configuration is valid, False otherwise
    """
    issues = []

    # Check API key
    if config.API_KEY == "your-secret-api-key-here-generate-random-string":
        issues.append("API_KEY is still using default value. Please set a secure random key.")

    # Check Qdrant connection
    if config.QDRANT_HOST == "localhost" and config.is_production:
        issues.append("Warning: Using localhost for Qdrant in production environment.")

    # Check embedding model
    if not config.EMBEDDING_MODEL:
        issues.append("EMBEDDING_MODEL is not set.")

    # Check LLM configuration
    if not config.OLLAMA_HOST or not config.OLLAMA_MODEL:
        issues.append("Ollama configuration (OLLAMA_HOST, OLLAMA_MODEL) is incomplete.")

    # Check data directories
    for dir_name, dir_path in [
        ("DATA_DIR", config.DATA_DIR),
        ("PROCESSED_DIR", config.PROCESSED_DIR),
        ("MODEL_CACHE_DIR", config.MODEL_CACHE_DIR),
    ]:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create {dir_name} at {dir_path}: {e}")

    # Print issues
    if issues:
        print("\n⚠️  Configuration Issues Found:")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        return False

    print("✓ Configuration validated successfully")
    return True


# ========================================
# Helper Functions
# ========================================
def print_config():
    """Print current configuration (excluding sensitive values)."""
    print("\n" + "=" * 60)
    print("Aviation RAG System Configuration")
    print("=" * 60)

    sections = {
        "Environment": [
            ("Environment", config.ENVIRONMENT),
            ("Debug", config.DEBUG),
        ],
        "Qdrant": [
            ("Host", config.QDRANT_HOST),
            ("Port", config.QDRANT_PORT),
            ("Collection", config.QDRANT_COLLECTION_NAME),
        ],
        "Ollama/LLM": [
            ("Host", config.OLLAMA_HOST),
            ("Model", config.OLLAMA_MODEL),
            ("Temperature", config.LLM_TEMPERATURE),
        ],
        "Embeddings": [
            ("Model", config.EMBEDDING_MODEL),
            ("Batch Size", config.EMBEDDING_BATCH_SIZE),
            ("Dimension", config.EMBEDDING_DIMENSION),
        ],
        "Search": [
            ("Top-K", config.SEARCH_TOP_K),
            ("Score Threshold", config.SEARCH_SCORE_THRESHOLD),
        ],
        "API": [
            ("Host", config.API_HOST),
            ("Port", config.API_PORT),
            ("Workers", config.API_WORKERS),
            ("Rate Limit", f"{config.RATE_LIMIT}/min"),
        ],
    }

    for section_name, items in sections.items():
        print(f"\n{section_name}:")
        for key, value in items:
            print(f"  {key:20s}: {value}")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    """Run configuration validation and print config when executed directly."""
    print_config()
    validate_config()
