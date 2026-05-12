from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..schemas.url import URLCreateRequest, URLCreateResponse
from ..services.url_service import (
    get_short_code_stats,
    create_short_url,
    get_url_mapping,
    update_access_time
)


router = APIRouter()


@router.get("/")
def root(db: Session = Depends(get_db)):
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


@router.get("/stats")
def get_stats_endpoint(db: Session = Depends(get_db)):
    return get_short_code_stats(db)


@router.post("/shorten", response_model=URLCreateResponse)
def create_short_url_endpoint(
    request: URLCreateRequest,
    db: Session = Depends(get_db)
):
    return create_short_url(db, request.url)


@router.get("/{short_code}")
def redirect_to_original(
    short_code: str,
    db: Session = Depends(get_db)
):
    url_mapping = get_url_mapping(db, short_code)
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    if url_mapping.review_status == "rejected":
        raise HTTPException(status_code=403, detail="This URL has been rejected due to content policy violation")
    
    update_access_time(db, url_mapping)
    
    return RedirectResponse(url=url_mapping.original_url, status_code=302)
