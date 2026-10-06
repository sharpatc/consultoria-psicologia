import os
from pathlib import Path

# Try to load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    # Root directory of the project
    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'psicologo_secret_key_12345')
    BASE_DIR = BASE_DIR
    DB_PATH = os.environ.get('DB_PATH', str(BASE_DIR / 'database.sqlite'))

    # Security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Email / SMTP configuration
    EMAIL_USER = os.environ.get('EMAIL_USER', '')
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '')
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    
    # Professional & Clinic Details
    CLINIC_NAME = os.environ.get('CLINIC_NAME', 'Zumaikira Bailey Psicologa')
    CLINIC_TITLE = os.environ.get('CLINIC_TITLE', 'PSICOLOGA - C.I.P. 8362')
    CLINIC_PHONE = os.environ.get('CLINIC_PHONE', '+507 6235-281')
    CLINIC_EMAIL = os.environ.get('CLINIC_EMAIL', 'Zumaikirabailey98@gmail.com')
    CLINIC_ADDRESS = os.environ.get('CLINIC_ADDRESS', 'Atlantic Plaza, 1er piso, local 127, oficina #224')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # If in production and secret key is default, warn or require strong key
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'


class TestingConfig(Config):
    """Testing configuration with in-memory or temporary database."""
    TESTING = True
    DEBUG = True
    DB_PATH = ':memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retrieve configuration based on FLASK_ENV or FLASK_CONFIG."""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    return config_by_name.get(env, DevelopmentConfig)
