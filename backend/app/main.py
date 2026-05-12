from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import APP_TITLE, APP_VERSION, setup_logging, get_logger
from .database.connection import Base, engine
from .routers.url import router as url_router
from .routers.admin import router as admin_router


setup_logging()
logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)


app = FastAPI(title=APP_TITLE, version=APP_VERSION)
logger.info(f"Application started - {APP_TITLE} v{APP_VERSION}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(url_router)
app.include_router(admin_router)
