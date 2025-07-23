"""
Configuration settings for the Binance Volatility Strategy application
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/binance_strategy')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_ALGORITHM = 'HS256'

    # Binance API settings (will be stored per user in database)
    BINANCE_API_BASE_URL = 'https://api.binance.com'
    BINANCE_TESTNET_BASE_URL = 'https://testnet.binance.vision'
    USE_TESTNET = os.getenv('USE_TESTNET', 'False').lower() == 'true'

    # Strategy settings
    DEFAULT_TARGET_LTV_MIN = 0.55
    DEFAULT_TARGET_LTV_MAX = 0.65
    DANGER_LTV_THRESHOLD = 0.70
    EMERGENCY_LTV_THRESHOLD = 0.75

    # Automation settings
    AUTOMATION_INTERVAL_MINUTES = int(os.getenv('AUTOMATION_INTERVAL_MINUTES', 5))
    MAX_SLIPPAGE_PERCENT = float(os.getenv('MAX_SLIPPAGE_PERCENT', 1.0))

    # Security
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))

    # Email notifications
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    FROM_EMAIL = os.getenv('FROM_EMAIL')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Railway deployment
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_TESTNET = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URL', 'sqlite:///dev_binance_strategy.db')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_TESTNET = False

    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    USE_TESTNET = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
