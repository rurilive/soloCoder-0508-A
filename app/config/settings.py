import os
from typing import Optional


class Config:
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DATABASE_PATH: str = os.environ.get('DATABASE_PATH', 'calendar.db')
    DEBUG: bool = os.environ.get('DEBUG', 'True').lower() == 'true'
    HOST: str = os.environ.get('HOST', '0.0.0.0')
    PORT: int = int(os.environ.get('PORT', '1111'))


class DevelopmentConfig(Config):
    DEBUG: bool = True


class ProductionConfig(Config):
    DEBUG: bool = False


def get_config() -> Config:
    env: str = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
