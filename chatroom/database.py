from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./chatroom.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="room")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    room = relationship("Room", back_populates="messages")
    is_private = Column(Integer, default=0)
    target_nickname = Column(String, index=True)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_all_rooms(db):
    return db.query(Room).order_by(Room.created_at.desc()).all()


def create_room(db, name: str):
    db_room = Room(name=name)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


def get_room_by_name(db, name: str):
    return db.query(Room).filter(Room.name == name).first()


def get_recent_messages(db, room_id: int, limit: int = 20):
    return db.query(Message).filter(Message.room_id == room_id, Message.is_private == 0).order_by(Message.timestamp.desc()).limit(limit).all()[::-1]


def save_message(db, nickname: str, content: str, room_id: int, is_private: int = 0, target_nickname: str = None):
    db_message = Message(
        nickname=nickname,
        content=content,
        room_id=room_id,
        is_private=is_private,
        target_nickname=target_nickname
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message
