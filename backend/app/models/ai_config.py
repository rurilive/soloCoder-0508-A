from datetime import datetime

from sqlalchemy import Column, String, DateTime

from ..database.connection import Base


class AIConfig(Base):
    __tablename__ = "ai_config"

    id = Column(String, primary_key=True, default="default")
    base_url = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    model = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
