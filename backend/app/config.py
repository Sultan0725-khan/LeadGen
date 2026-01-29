from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./leadgen.db"

    # LLM Configuration (Exclusive Offline Ollama support)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama2"

    # Google Places API
    google_places_api_key: Optional[str] = None

    # Email SMTP
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    # Email SendGrid
    sendgrid_api_key: Optional[str] = None

    # Email settings
    email_from_address: str = "noreply@example.com"
    email_from_name: str = "LeadGen System"
    max_emails_per_minute: int = 10
    default_language: str = "DE"

    # Salesforce Configuration
    sfdc_client_id: Optional[str] = None
    sfdc_client_secret: Optional[str] = None
    sfdc_username: Optional[str] = None
    sfdc_password: Optional[str] = None
    sfdc_security_token: Optional[str] = None
    sfdc_instance_url: Optional[str] = None  # e.g., https://playground-dev-ed.my.salesforce.com
    sfdc_is_sandbox: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
