from datetime import timedelta
from urllib.parse import quote_plus
import os

def _pg_url():
    user = os.environ.get("POSTGRES_USER", "fds_user")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "password")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db   = os.environ.get("POSTGRES_DB", "fds_db")
    return f"postgresql://{user}:{quote_plus(pwd)}@{host}:{port}/{db}"

class Config:
    SECRET_KEY                  = os.environ.get("SECRET_KEY", "dev-secret-min-32-chars-change!!")
    JWT_SECRET_KEY              = os.environ.get("JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "jwt-secret"))
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES   = timedelta(days=30)
    DEBUG                       = False
    SQLALCHEMY_DATABASE_URI     = _pg_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS   = {"pool_pre_ping": True, "pool_recycle": 300, "pool_size": 5, "max_overflow": 10}
    REDIS_HOST                  = os.environ.get("REDIS_HOST", "redis")
    REDIS_PORT                  = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD              = os.environ.get("REDIS_PASSWORD", "")
    REDIS_DB                    = int(os.environ.get("REDIS_DB", 0))
    MAIL_SERVER                 = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT                   = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS                = True
    MAIL_USERNAME               = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD               = os.environ.get("MAIL_PASSWORD", "")
    MAIL_SUPPRESS_SEND          = not bool(os.environ.get("MAIL_USERNAME", ""))
    ALLOWED_COUNTRIES           = os.environ.get("ALLOWED_COUNTRIES", "MA,FR,US,GB,DE,ES,IT,CA").split(",")
    MAX_TXN_IN_WINDOW           = int(os.environ.get("MAX_TXN_IN_WINDOW", 5))
    FREQ_WINDOW_MIN             = int(os.environ.get("FREQ_WINDOW_MIN", 10))
    DUP_WINDOW_MIN              = int(os.environ.get("DUP_WINDOW_MIN", 5))
    AMOUNT_MULTIPLIER           = float(os.environ.get("AMOUNT_MULTIPLIER", 2.0))
    CORS_ORIGINS                = os.environ.get("CORS_ORIGINS", "*")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return ProductionConfig() if env == "production" else DevelopmentConfig()
