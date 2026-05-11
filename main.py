import random
import string
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, func, desc
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


class URLMapping(Base):
    __tablename__ = "url_mappings"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, index=True)


Base.metadata.create_all(bind=engine)


class URLCreateRequest(BaseModel):
    url: str


class URLCreateResponse(BaseModel):
    short_code: str
    original_url: str
    is_reused: bool = False
    replaced_url: str | None = None


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
    
    oldest = db.query(URLMapping).order_by(URLMapping.last_accessed_at.asc()).first()
    newest = db.query(URLMapping).order_by(URLMapping.last_accessed_at.desc()).first()
    
    return {
        "total_pool": TOTAL_SHORT_CODE_POOL,
        "used_count": used_count,
        "available_count": available_count,
        "usage_percent": round(usage_percent, 4),
        "oldest_accessed": oldest.last_accessed_at.isoformat() if oldest else None,
        "newest_accessed": newest.last_accessed_at.isoformat() if newest else None
    }


app = FastAPI(title="URL Shortener Service (LRU)", version="1.1.0")


@app.get("/")
def root():
    db = next(get_db())
    stats = get_short_code_stats(db)
    return {
        "service": "URL Shortener with LRU Replacement",
        "strategy": "When pool is full, replace the least recently used short code",
        "short_code_pool": stats,
        "endpoints": {
            "POST /shorten": "Create a short URL (uses LRU replacement when pool is full)",
            "GET /{short_code}": "Redirect to original URL and update access time",
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
        existing.last_accessed_at = datetime.utcnow()
        db.commit()
        return URLCreateResponse(
            short_code=existing.short_code,
            original_url=existing.original_url,
            is_reused=False,
            replaced_url=None
        )
    
    short_code = None
    for attempt in range(MAX_SHORT_CODE_ATTEMPTS):
        candidate = generate_short_code()
        if not db.query(URLMapping).filter(URLMapping.short_code == candidate).first():
            short_code = candidate
            break
    
    replaced_url = None
    is_reused = False
    
    if short_code is None:
        lru_record = db.query(URLMapping).order_by(URLMapping.last_accessed_at.asc()).first()
        
        if lru_record is None:
            raise HTTPException(
                status_code=500,
                detail="Unexpected error: No records found in database"
            )
        
        replaced_url = lru_record.original_url
        short_code = lru_record.short_code
        is_reused = True
        
        lru_record.original_url = request.url
        lru_record.last_accessed_at = datetime.utcnow()
        db.commit()
        db.refresh(lru_record)
        
        return URLCreateResponse(
            short_code=short_code,
            original_url=request.url,
            is_reused=True,
            replaced_url=replaced_url
        )
    
    url_mapping = URLMapping(
        short_code=short_code,
        original_url=request.url
    )
    db.add(url_mapping)
    db.commit()
    db.refresh(url_mapping)
    
    return URLCreateResponse(
        short_code=short_code,
        original_url=request.url,
        is_reused=False,
        replaced_url=None
    )


@app.get("/{short_code}")
def redirect_to_original(short_code: str):
    db = next(get_db())
    
    url_mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    url_mapping.last_accessed_at = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url=url_mapping.original_url, status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=1111, reload=True)
