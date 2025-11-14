"""Application configuration."""
import os
from pydantic_settings import BaseSettings
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:123456789@localhost:3306/nigerian_grants_db")
    
    # WhatsApp Providers
    whatsapp_provider: str = os.getenv("WHATSAPP_PROVIDER", "twilio")
    
    # Meta WhatsApp Cloud API
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_api_version: str = os.getenv("WHATSAPP_API_VERSION", "v18.0")
    
    # Twilio WhatsApp
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_whatsapp_number: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
    
    # LLM Configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    llm_model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    
    # RAG Configuration
    rag_vector_store: str = os.getenv("RAG_VECTOR_STORE", "chroma")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    chromadb_disable_telemetry: bool = os.getenv("CHROMADB_DISABLE_TELEMETRY", "true").lower() == "true"
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
    embedding_service_url: str = os.getenv("EMBEDDING_SERVICE_URL", "")
    embedding_service_api_key: str = os.getenv("EMBEDDING_SERVICE_API_KEY", "")
    
    # Crawler Configuration
    crawler_user_agent: str = os.getenv("CRAWLER_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    crawler_timeout: int = int(os.getenv("CRAWLER_TIMEOUT", "30"))
    crawler_max_retries: int = int(os.getenv("CRAWLER_MAX_RETRIES", "3"))
    crawler_backoff_factor: int = int(os.getenv("CRAWLER_BACKOFF_FACTOR", "2"))
    
    # Application
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
    
    # Cron Schedule
    cron_schedule: str = os.getenv("CRON_SCHEDULE", "0 6 * * *")
    
    # File Storage
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    pdf_storage_dir: str = os.getenv("PDF_STORAGE_DIR", "./storage/pdfs")
    
    # Content Filter
    enable_content_filter: bool = os.getenv("ENABLE_CONTENT_FILTER", "true").lower() == "true"
    content_filter_model: str = os.getenv("CONTENT_FILTER_MODEL", "unitary/toxic-bert")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

