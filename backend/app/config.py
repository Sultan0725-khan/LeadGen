from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./leadgen.db"

    # OpenAI
    openai_api_key: str

    # Google Places API
    google_places_api_key: Optional[str] = None

    # Yelp Fusion API
    yelp_api_key: Optional[str] = None

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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
