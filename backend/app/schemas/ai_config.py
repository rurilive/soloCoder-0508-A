from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AIConfigCreate(BaseModel):
    base_url: str
    api_key: str
    model: str


class AIConfigResponse(BaseModel):
    id: str
    base_url: str
    model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchReviewRequest(BaseModel):
    short_codes: list[str]


class BatchReviewResult(BaseModel):
    short_code: str
    status: str
    comment: Optional[str] = None
    error: Optional[str] = None


class BatchReviewResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: list[BatchReviewResult]
