import string
import os
import logging
import sys


DATABASE_URL = "sqlite:///./url_shortener.db"

SHORT_CODE_LENGTH = 6
CHARACTERS = string.ascii_letters + string.digits

MAX_SHORT_CODE_ATTEMPTS = 100
CONSECUTIVE_HIT_THRESHOLD = 5
INITIAL_RANDOM_ATTEMPTS = 3

APP_TITLE = "URL Shortener Service (LRU)"
APP_VERSION = "1.2.0"
APP_HOST = "0.0.0.0"
APP_PORT = 1111

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_SECRET = os.getenv("JWT_SECRET", "secret-key-change-in-production")
JWT_EXPIRE_MINUTES = 60


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )
    
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.DEBUG)


def get_logger(name: str):
    return logging.getLogger(name)
