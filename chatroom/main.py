from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
from sqlalchemy.orm import Session
import json
from datetime import datetime
import re

from .database import get_db, get_recent_messages, save_message, get_all_rooms, create_room, get_room_by_name, get_private_rooms_for_user

app = FastAPI(title="Real-time Chatroom")

templates = Jinja2Templates(directory="chatroom/templates")


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, room: str, nickname: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = {}
        self.rooms[room][nickname] = websocket
        self.user_connections[nickname] = websocket

    def disconnect(self, websocket: WebSocket, room: str, nickname: str):
        if room in self.rooms and nickname in self.rooms[room]:
            del self.rooms[room][nickname]
            if not self.rooms[room]:
                del self.rooms[room]
        if nickname in self.user_connections:
            del self.user_connections[nickname]

    async def broadcast(self, message: dict, room: str):
        if room in self.rooms:
            for connection in self.rooms[room].values():
                await connection.send_json(message)

    async def broadcast_to_all(self, message: dict):
        for room in self.rooms:
            for connection in self.rooms[room].values():
                await connection.send_json(message)

    async def send_private_global(self, message: dict, target_nickname: str, sender_nickname: str):
        if target_nickname in self.user_connections:
            await self.user_connections[target_nickname].send_json(message)
        if sender_nickname in self.user_connections:
            await self.user_connections[sender_nickname].send_json(message)

    async def send_private(self, message: dict, room: str, target_nickname: str, sender_nickname: str):
        if room in self.rooms:
            if target_nickname in self.rooms[room]:
                await self.rooms[room][target_nickname].send_json(message)
            if sender_nickname in self.rooms[room]:
                await self.rooms[room][sender_nickname].send_json(message)

    def get_users_in_room(self, room: str) -> List[str]:
        if room in self.rooms:
            return list(self.rooms[room].keys())
        return []

    def get_all_room_user_counts(self) -> Dict[str, int]:
        return {room: len(users) for room, users in self.rooms.items()}

    def get_user_current_room(self, nickname: str) -> str:
        for room, users in self.rooms.items():
            if nickname in users:
                return room
        return None


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def get(request: Request, db: Session = Depends(get_db)):
    rooms = get_all_rooms(db)
    if not rooms:
        default_room = create_room(db, "默认房间")
        rooms = [default_room]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"rooms": rooms}
    )


@app.get("/api/rooms")
async def get_rooms(db: Session = Depends(get_db)):
    rooms = get_all_rooms(db)
    return {"rooms": [{"name": room.name} for room in rooms]}


@app.post("/api/rooms")
async def create_new_room(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    room_name = data.get("name")
    if not room_name:
        return {"success": False, "error": "房间名称不能为空"}
    existing = get_room_by_name(db, room_name)
    if existing:
        return {"success": False, "error": "房间已存在"}
    create_room(db, room_name)
    return {"success": True}


@app.get("/api/rooms/{room_name}/messages")
async def get_room_messages(room_name: str, db: Session = Depends(get_db)):
    room = get_room_by_name(db, room_name)
    if not room:
        return {"messages": []}
    messages = get_recent_messages(db, room.id)
    return {"messages": [{"nickname": m.nickname, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in messages]}


@app.get("/api/rooms/{room_name}/users")
async def get_room_users(room_name: str):
    users = manager.get_users_in_room(room_name)
    return {"users": users}


@app.get("/api/rooms/users/counts")
async def get_all_room_user_counts():
    counts = manager.get_all_room_user_counts()
    return {"counts": counts}


@app.get("/api/users/{nickname}/private-rooms")
async def get_user_private_rooms(nickname: str, db: Session = Depends(get_db)):
    private_rooms = get_private_rooms_for_user(db, nickname)
    return {"private_rooms": private_rooms}


def is_user_in_private_room(room_name: str, nickname: str) -> bool:
    if not room_name.startswith('private:'):
        return True
    parts = room_name.split(':')
    if len(parts) != 3:
        return False
    return parts[1] == nickname or parts[2] == nickname


@app.websocket("/ws/{room}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room: str, nickname: str, db: Session = Depends(get_db)):
    db_room = get_room_by_name(db, room)
    
    if not db_room:
        if room.startswith('private:'):
            parts = room.split(':')
            if len(parts) == 3 and (parts[1] == nickname or parts[2] == nickname):
                db_room = create_room(db, room, 1)
            else:
                await websocket.close()
                return
        else:
            await websocket.close()
            return
    
    if room.startswith('private:') and not is_user_in_private_room(room, nickname):
        await websocket.close()
        return

    await manager.connect(websocket, room, nickname)
    
    users = manager.get_users_in_room(room)
    await manager.broadcast({
        "type": "user_list",
        "users": users
    }, room)
    
    room_user_counts = manager.get_all_room_user_counts()
    await manager.broadcast_to_all({
        "type": "room_user_counts",
        "counts": room_user_counts
    })

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            content = message_data.get("content", "")
            
            if content.strip():
                timestamp = datetime.utcnow().isoformat()
                
                private_match = re.match(r'^@(\w+)\s+(.+)$', content)
                
                if private_match:
                    target_nickname = private_match.group(1)
                    private_content = private_match.group(2)
                    
                    private_room_name = f"private:{nickname}:{target_nickname}"
                    private_room_name_alt = f"private:{target_nickname}:{nickname}"
                    
                    db_private_room = get_room_by_name(db, private_room_name) or get_room_by_name(db, private_room_name_alt)
                    if not db_private_room:
                        db_private_room = create_room(db, private_room_name, 1)
                    
                    save_message(db, nickname, content, db_private_room.id, 1, target_nickname)
                    
                    await manager.send_private_global({
                        "type": "private_message",
                        "nickname": nickname,
                        "target_nickname": target_nickname,
                        "content": private_content,
                        "timestamp": timestamp,
                        "private_room": private_room_name
                    }, target_nickname, nickname)
                else:
                    save_message(db, nickname, content, db_room.id)
                    
                    await manager.broadcast({
                        "type": "message",
                        "nickname": nickname,
                        "content": content,
                        "timestamp": timestamp
                    }, room)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room, nickname)
        users = manager.get_users_in_room(room)
        await manager.broadcast({
            "type": "user_list",
            "users": users
        }, room)
        
        room_user_counts = manager.get_all_room_user_counts()
        await manager.broadcast_to_all({
            "type": "room_user_counts",
            "counts": room_user_counts
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1111)
