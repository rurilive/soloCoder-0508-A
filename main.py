import uvicorn

from backend.app.config.settings import APP_HOST, APP_PORT
from backend.app.main import app


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
