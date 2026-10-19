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
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    IS_PRODUCTION = False

    # Security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    
    # Email / SMTP configuration
    EMAIL_USER = os.environ.get('EMAIL_USER', '')
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '')
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    TIMEZONE = os.environ.get('TIMEZONE', 'America/Panama')
    APPOINTMENT_REMINDER_HOUR = int(os.environ.get('APPOINTMENT_REMINDER_HOUR', 8))
    APPOINTMENT_REMINDER_MAX_ATTEMPTS = int(
        os.environ.get('APPOINTMENT_REMINDER_MAX_ATTEMPTS', 4)
    )
    APPOINTMENT_REMINDER_RETRY_MINUTES = int(
        os.environ.get('APPOINTMENT_REMINDER_RETRY_MINUTES', 15)
    )
    
    # Professional & Clinic Details
    CLINIC_NAME = os.environ.get('CLINIC_NAME', 'PsicoEmocional')
    CLINIC_TITLE = os.environ.get('CLINIC_TITLE', 'Psicologia y bienestar emocional')
    CLINIC_PHONE = os.environ.get('CLINIC_PHONE', '+507 6235-281')
    CLINIC_EMAIL = os.environ.get('CLINIC_EMAIL', 'Zumaikirabailey98@gmail.com')
    CLINIC_ADDRESS = os.environ.get('CLINIC_ADDRESS', 'Atlantic Plaza, 1er piso, local 127, oficina #224')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    IS_PRODUCTION = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'


class TestingConfig(Config):
    """Testing configuration with in-memory or temporary database."""
    TESTING = True
    DEBUG = True
    DB_PATH = ':memory:'
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'


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
