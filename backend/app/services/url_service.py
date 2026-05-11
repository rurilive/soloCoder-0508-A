from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func

from ..config.settings import (
    MAX_SHORT_CODE_ATTEMPTS,
    CONSECUTIVE_HIT_THRESHOLD,
    INITIAL_RANDOM_ATTEMPTS,
)
from ..models.url import URLMapping
from ..schemas.url import URLCreateResponse
from ..utils.short_code import generate_short_code, TOTAL_SHORT_CODE_POOL


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
        "newest_accessed": newest.last_accessed_at.isoformat() if newest else None,
    }


def get_url_mapping(db, short_code: str):
    return db.query(URLMapping).filter(URLMapping.short_code == short_code).first()


def update_access_time(db, url_mapping):
    url_mapping.last_accessed_at = datetime.utcnow()
    db.commit()
    db.refresh(url_mapping)


def get_lru_record(db):
    return db.query(URLMapping).order_by(URLMapping.last_accessed_at.asc()).first()


def perform_lru_replacement(db, url: str):
    lru_record = get_lru_record(db)

    if lru_record is None:
        raise HTTPException(
            status_code=500,
            detail="Unexpected error: No records found in database",
        )

    replaced_url = lru_record.original_url
    short_code = lru_record.short_code

    lru_record.original_url = url
    lru_record.last_accessed_at = datetime.utcnow()
    db.commit()
    db.refresh(lru_record)

    return URLCreateResponse(
        short_code=short_code,
        original_url=url,
        is_reused=True,
        replaced_url=replaced_url,
    )


def create_short_url(db, url: str):
    existing = db.query(URLMapping).filter(URLMapping.original_url == url).first()
    if existing:
        update_access_time(db, existing)
        return URLCreateResponse(
            short_code=existing.short_code,
            original_url=existing.original_url,
            is_reused=False,
            replaced_url=None,
        )

    short_code = None
    consecutive_hits = 0
    total_attempts = 0

    while total_attempts < MAX_SHORT_CODE_ATTEMPTS:
        candidate = generate_short_code()
        total_attempts += 1

        if not db.query(URLMapping).filter(URLMapping.short_code == candidate).first():
            short_code = candidate
            break

        consecutive_hits += 1

        if consecutive_hits >= CONSECUTIVE_HIT_THRESHOLD:
            return perform_lru_replacement(db, url)

        if total_attempts >= INITIAL_RANDOM_ATTEMPTS and consecutive_hits >= 2:
            return perform_lru_replacement(db, url)

    if short_code is None:
        return perform_lru_replacement(db, url)

    url_mapping = URLMapping(
        short_code=short_code,
        original_url=url,
    )
    db.add(url_mapping)
    db.commit()
    db.refresh(url_mapping)

    return URLCreateResponse(
        short_code=short_code,
        original_url=url,
        is_reused=False,
        replaced_url=None,
    )
