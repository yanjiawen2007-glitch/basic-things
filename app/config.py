"""
Application configuration
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./data/scheduler.db"
    
    # Scheduler
    max_workers: int = 10
    job_defaults_coalesce: bool = True
    job_defaults_max_instances: int = 1
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"
    
    # Notifications (placeholder)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
