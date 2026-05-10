import random
import string
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, func
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
MAX_SHORT_CODE_ATTEMPTS = 100
WARNING_THRESHOLD_PERCENT = 90


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


TOTAL_SHORT_CODE_POOL = len(CHARACTERS) ** SHORT_CODE_LENGTH


def generate_short_code() -> str:
    return "".join(random.choices(CHARACTERS, k=SHORT_CODE_LENGTH))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_short_code_stats(db):
    used_count = db.query(func.count(URLMapping.short_code)).scalar()
    available_count = TOTAL_SHORT_CODE_POOL - used_count
    usage_percent = (used_count / TOTAL_SHORT_CODE_POOL) * 100
    return {
        "total_pool": TOTAL_SHORT_CODE_POOL,
        "used_count": used_count,
        "available_count": available_count,
        "usage_percent": round(usage_percent, 4)
    }


app = FastAPI(title="URL Shortener Service", version="1.0.0")


@app.get("/")
def root():
    db = next(get_db())
    stats = get_short_code_stats(db)
    return {
        "service": "URL Shortener",
        "short_code_pool": stats,
        "endpoints": {
            "POST /shorten": "Create a short URL",
            "GET /{short_code}": "Redirect to original URL",
            "GET /stats": "Get short code pool statistics"
        }
    }


@app.get("/stats")
def get_stats_endpoint():
    db = next(get_db())
    return get_short_code_stats(db)


@app.post("/shorten", response_model=URLCreateResponse)
def create_short_url(request: URLCreateRequest):
    db = next(get_db())
    
    existing = db.query(URLMapping).filter(URLMapping.original_url == request.url).first()
    if existing:
        return URLCreateResponse(
            short_code=existing.short_code,
            original_url=existing.original_url
        )
    
    stats = get_short_code_stats(db)
    if stats["available_count"] == 0:
        raise HTTPException(
            status_code=507,
            detail=f"Short code pool exhausted. All {stats['total_pool']:,} short codes are in use."
        )
    
    short_code = None
    for attempt in range(MAX_SHORT_CODE_ATTEMPTS):
        candidate = generate_short_code()
        if not db.query(URLMapping).filter(URLMapping.short_code == candidate).first():
            short_code = candidate
            break
    
    if short_code is None:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate unique short code after {MAX_SHORT_CODE_ATTEMPTS} attempts. "
                   f"Pool usage: {stats['usage_percent']}%. "
                   f"Available: {stats['available_count']:,}"
        )
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=1111, reload=True)
