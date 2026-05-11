from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Text

from ..database.connection import Base


class URLMapping(Base):
    __tablename__ = "url_mappings"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, index=True)
    access_count = Column(Integer, default=0)
    review_status = Column(String, default="pending")
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
