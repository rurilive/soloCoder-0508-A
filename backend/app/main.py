from fastapi import FastAPI

from .config.settings import APP_TITLE, APP_VERSION
from .database.connection import Base, engine
from .routers.url import router as url_router


Base.metadata.create_all(bind=engine)


app = FastAPI(title=APP_TITLE, version=APP_VERSION)

app.include_router(url_router)
