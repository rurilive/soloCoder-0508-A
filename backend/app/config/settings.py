import string


DATABASE_URL = "sqlite:///./url_shortener.db"

SHORT_CODE_LENGTH = 6
CHARACTERS = string.ascii_letters + string.digits
MAX_SHORT_CODE_ATTEMPTS = 100

APP_TITLE = "URL Shortener Service (LRU)"
APP_VERSION = "1.1.0"
APP_HOST = "0.0.0.0"
APP_PORT = 1111
