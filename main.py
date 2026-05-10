import random
import string
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./url_shortener.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SHORT_CODE_LENGTH = 6
CHARACTERS = string.ascii_letters + string.digits


class URLMapping(Base):
    __tablename__ = "url_mappings"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class URLCreateRequest(BaseModel):
    url: str


class URLCreateResponse(BaseModel):
    short_code: str
    original_url: str


def generate_short_code() -> str:
    return "".join(random.choices(CHARACTERS, k=SHORT_CODE_LENGTH))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="URL Shortener Service", version="1.0.0")


@app.post("/shorten", response_model=URLCreateResponse)
def create_short_url(request: URLCreateRequest):
    db = next(get_db())
    
    existing = db.query(URLMapping).filter(URLMapping.original_url == request.url).first()
    if existing:
        return URLCreateResponse(
            short_code=existing.short_code,
            original_url=existing.original_url
        )
    
    while True:
        short_code = generate_short_code()
        if not db.query(URLMapping).filter(URLMapping.short_code == short_code).first():
            break
    
    url_mapping = URLMapping(
        short_code=short_code,
        original_url=request.url
    )
    db.add(url_mapping)
    db.commit()
    db.refresh(url_mapping)
    
    return URLCreateResponse(
        short_code=url_mapping.short_code,
        original_url=url_mapping.original_url
    )


@app.get("/{short_code}")
def redirect_to_original(short_code: str):
    db = next(get_db())
    
    url_mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    return RedirectResponse(url=url_mapping.original_url, status_code=302)


@app.get("/")
def root():
    return {
        "service": "URL Shortener",
        "endpoints": {
            "POST /shorten": "Create a short URL",
            "GET /{short_code}": "Redirect to original URL"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=1111, reload=True)
