from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./chatroom.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_recent_messages(db, limit: int = 20):
    return db.query(Message).order_by(Message.timestamp.desc()).limit(limit).all()[::-1]


def save_message(db, nickname: str, content: str):
    db_message = Message(nickname=nickname, content=content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message
