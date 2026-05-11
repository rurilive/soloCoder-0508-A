from datetime import datetime

from sqlalchemy import Column, String, DateTime

from ..database.connection import Base


class URLMapping(Base):
    __tablename__ = "url_mappings"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, index=True)
