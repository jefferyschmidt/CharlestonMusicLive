"""
Production configuration for MusicLive.
"""
import os
from typing import Dict, Any

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
)

# R2 Storage configuration
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "musiclive-artifacts")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "4"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Crawler configuration
CRAWLER_MAX_SOURCES = int(os.getenv("CRAWLER_MAX_SOURCES", "50"))
CRAWLER_MAX_CONCURRENT = int(os.getenv("CRAWLER_MAX_CONCURRENT", "3"))
CRAWLER_RATE_LIMIT = float(os.getenv("CRAWLER_RATE_LIMIT", "1.0"))
CRAWLER_RESPECT_ROBOTS = os.getenv("CRAWLER_RESPECT_ROBOTS", "true").lower() == "true"

# Artist research configuration
ARTIST_RESEARCH_ENABLED = os.getenv("ARTIST_RESEARCH_ENABLED", "true").lower() == "true"
ARTIST_RESEARCH_MAX_CONCURRENT = int(os.getenv("ARTIST_RESEARCH_MAX_CONCURRENT", "5"))
ARTIST_RESEARCH_RATE_LIMIT = float(os.getenv("ARTIST_RESEARCH_RATE_LIMIT", "0.5"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# Monitoring configuration
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_INTERVAL = int(os.getenv("METRICS_INTERVAL", "60"))

# Fly.io configuration
FLY_APP_NAME = os.getenv("FLY_APP_NAME", "musiclive")
FLY_REGION = os.getenv("FLY_REGION", "iad")

def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    return {
        "url": DATABASE_URL,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600"))
    }

def get_crawler_config() -> Dict[str, Any]:
    """Get crawler configuration."""
    return {
        "max_sources": CRAWLER_MAX_SOURCES,
        "max_concurrent": CRAWLER_MAX_CONCURRENT,
        "rate_limit": CRAWLER_RATE_LIMIT,
        "respect_robots": CRAWLER_RESPECT_ROBOTS,
        "user_agent": os.getenv("CRAWLER_USER_AGENT", "Mozilla/5.0 (compatible; MusicLiveBot/1.0; +https://musiclive.com/bot)"),
        "timeout": int(os.getenv("CRAWLER_TIMEOUT", "30")),
        "retry_attempts": int(os.getenv("CRAWLER_RETRY_ATTEMPTS", "3"))
    }

def get_api_config() -> Dict[str, Any]:
    """Get API configuration."""
    return {
        "host": API_HOST,
        "port": API_PORT,
        "workers": API_WORKERS,
        "debug": DEBUG,
        "secret_key": SECRET_KEY,
        "allowed_hosts": ALLOWED_HOSTS
    }

def get_storage_config() -> Dict[str, Any]:
    """Get storage configuration."""
    return {
        "r2_account_id": R2_ACCOUNT_ID,
        "r2_access_key_id": R2_ACCESS_KEY_ID,
        "r2_secret_access_key": R2_SECRET_ACCESS_KEY,
        "r2_bucket_name": R2_BUCKET_NAME,
        "local_fallback": os.getenv("STORAGE_LOCAL_FALLBACK", "true").lower() == "true"
    }

def get_monitoring_config() -> Dict[str, Any]:
    """Get monitoring configuration."""
    return {
        "enable_metrics": ENABLE_METRICS,
        "metrics_interval": METRICS_INTERVAL,
        "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT
    }

# Validate required configuration
def validate_config():
    """Validate that all required configuration is present."""
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not globals().get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

# Auto-validate on import
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise
