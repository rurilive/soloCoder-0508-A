from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, text
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
    is_private = Column(Integer, default=0)
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


def migrate_database():
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(rooms)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'is_private' not in columns:
            conn.execute(text("ALTER TABLE rooms ADD COLUMN is_private INTEGER DEFAULT 0"))
            print("Added is_private column to rooms table")
        
        result = conn.execute(text("PRAGMA table_info(messages)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'is_private' not in columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN is_private INTEGER DEFAULT 0"))
            print("Added is_private column to messages table")
        
        if 'target_nickname' not in columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN target_nickname VARCHAR"))
            print("Added target_nickname column to messages table")
        
        if 'room_id' not in columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN room_id INTEGER"))
            print("Added room_id column to messages table")
        
        conn.commit()


Base.metadata.create_all(bind=engine)
migrate_database()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_all_rooms(db):
    return db.query(Room).filter(Room.is_private == 0).order_by(Room.created_at.desc()).all()


def create_room(db, name: str, is_private: int = 0):
    db_room = Room(name=name, is_private=is_private)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


def get_room_by_name(db, name: str):
    return db.query(Room).filter(Room.name == name).first()


def get_recent_messages(db, room_id: int, limit: int = 20):
    room = db.query(Room).filter(Room.id == room_id).first()
    if room and room.is_private:
        return db.query(Message).filter(Message.room_id == room_id).order_by(Message.timestamp.desc()).limit(limit).all()[::-1]
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


def get_private_rooms_for_user(db, nickname: str):
    private_rooms = db.query(Room).filter(Room.is_private == 1).all()
    user_private_rooms = []
    for room in private_rooms:
        if room.name.startswith('private:'):
            parts = room.name.split(':')
            if len(parts) == 3 and (parts[1] == nickname or parts[2] == nickname):
                other_user = parts[2] if parts[1] == nickname else parts[1]
                user_private_rooms.append({
                    'name': room.name,
                    'other_user': other_user
                })
    return user_private_rooms
