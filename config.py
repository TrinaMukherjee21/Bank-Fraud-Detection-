"""
Configuration management for Bank Fraud Detection System
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_PREDICTION = "10 per minute"
    
    # Model settings
    MODEL_DIR = os.path.join(os.path.dirname(__file__), 'model')
    MODEL_FILE = 'fraud_model.pkl'
    ENCODERS_FILE = 'label_encoders.pkl'
    THRESHOLD_FILE = 'threshold.pkl'
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'fraud_detection.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Data validation
    MAX_TRANSACTION_AMOUNT = 1000000
    MIN_TRANSACTION_AMOUNT = 0.01
    MAX_TIME_STEP = 1000
    MAX_CATEGORY_VALUE = 20
    
    # Performance monitoring
    ENABLE_METRICS = True
    METRICS_RETENTION_DAYS = 30

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    RATELIMIT_ENABLED = True
    
    # Enhanced security for production
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Production logging
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment variable"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])