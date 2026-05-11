from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class URLMappingAdminResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    last_accessed_at: datetime
    access_count: int
    review_status: str
    review_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class URLListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[URLMappingAdminResponse]

class ReviewURLRequest(BaseModel):
    short_code: str
    status: str
    comment: Optional[str] = None

class AIReviewRequest(BaseModel):
    short_code: str
    base_url: str
    api_key: str
    model: str

class AIReviewResponse(BaseModel):
    status: str
    comment: str
