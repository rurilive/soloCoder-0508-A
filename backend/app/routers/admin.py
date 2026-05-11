from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models.url import URLMapping
from ..schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    URLMappingAdminResponse,
    URLListResponse,
    ReviewURLRequest,
    AIReviewRequest,
    AIReviewResponse
)
from ..services.ai_service import review_url_with_ai, AIConfig
from ..utils.auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    if not authenticate_admin(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": request.username})
    return AdminLoginResponse(access_token=access_token)

@router.get("/urls", response_model=URLListResponse)
async def get_urls(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    review_status: str = Query(None)
):
    query = db.query(URLMapping)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (URLMapping.short_code.like(search_pattern)) |
            (URLMapping.original_url.like(search_pattern))
        )
    
    if review_status:
        query = query.filter(URLMapping.review_status == review_status)
    
    total = query.count()
    
    items = (
        query
        .order_by(URLMapping.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return URLListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[URLMappingAdminResponse.model_validate(item) for item in items]
    )

@router.get("/urls/{short_code}", response_model=URLMappingAdminResponse)
async def get_url_detail(
    short_code: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    url_mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="短码不存在")
    
    return URLMappingAdminResponse.model_validate(url_mapping)

@router.post("/urls/review")
async def review_url(
    request: ReviewURLRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    if request.status not in ["approved", "rejected", "pending", "needs_manual_review"]:
        raise HTTPException(status_code=400, detail="无效的审核状态")
    
    url_mapping = db.query(URLMapping).filter(URLMapping.short_code == request.short_code).first()
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="短码不存在")
    
    url_mapping.review_status = request.status
    url_mapping.review_comment = request.comment
    url_mapping.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(url_mapping)
    
    return URLMappingAdminResponse.model_validate(url_mapping)

@router.post("/urls/ai-review", response_model=AIReviewResponse)
async def ai_review_url(
    request: AIReviewRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    url_mapping = db.query(URLMapping).filter(URLMapping.short_code == request.short_code).first()
    
    if not url_mapping:
        raise HTTPException(status_code=404, detail="短码不存在")
    
    ai_config = AIConfig(
        base_url=request.base_url,
        api_key=request.api_key,
        model=request.model
    )
    
    result = await review_url_with_ai(url_mapping.original_url, ai_config)
    
    url_mapping.review_status = result.status
    url_mapping.review_comment = result.comment
    url_mapping.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(url_mapping)
    
    return result

@router.get("/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    total = db.query(func.count(URLMapping.short_code)).scalar()
    pending = db.query(func.count(URLMapping.short_code)).filter(URLMapping.review_status == "pending").scalar()
    approved = db.query(func.count(URLMapping.short_code)).filter(URLMapping.review_status == "approved").scalar()
    rejected = db.query(func.count(URLMapping.short_code)).filter(URLMapping.review_status == "rejected").scalar()
    needs_review = db.query(func.count(URLMapping.short_code)).filter(URLMapping.review_status == "needs_manual_review").scalar()
    total_accesses = db.query(func.sum(URLMapping.access_count)).scalar() or 0
    
    return {
        "total_urls": total,
        "pending_review": pending,
        "approved": approved,
        "rejected": rejected,
        "needs_manual_review": needs_review,
        "total_accesses": total_accesses
    }
