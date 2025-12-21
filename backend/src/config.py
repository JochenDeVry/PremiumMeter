"""
Application configuration management.
Loads environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "dev_secret_key_change_in_production"
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Database Configuration
    database_url: str = "postgresql://premiummeter:your_secure_password_here@127.0.0.1:5432/premiummeter"
    
    # Scraper Configuration (Intra-day Polling)
    polling_interval_minutes: int = 5  # Default: 5 minutes
    market_hours_start: str = "09:30:00"  # Market open time
    market_hours_end: str = "16:00:00"    # Market close time
    default_timezone: str = "America/New_York"
    risk_free_rate: float = 0.045  # 4.5% for Black-Scholes calculations
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

# Global settings instance
settings = Settings()
