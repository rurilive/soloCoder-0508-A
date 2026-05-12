from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
from sqlalchemy.orm import Session
import json
from datetime import datetime
import re

from .database import get_db, get_recent_messages, save_message, get_all_rooms, create_room, get_room_by_name

app = FastAPI(title="Real-time Chatroom")

templates = Jinja2Templates(directory="chatroom/templates")


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str, nickname: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = {}
        self.rooms[room][nickname] = websocket

    def disconnect(self, websocket: WebSocket, room: str, nickname: str):
        if room in self.rooms and nickname in self.rooms[room]:
            del self.rooms[room][nickname]
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast(self, message: dict, room: str):
        if room in self.rooms:
            for connection in self.rooms[room].values():
                await connection.send_json(message)

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


@app.websocket("/ws/{room}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room: str, nickname: str, db: Session = Depends(get_db)):
    db_room = get_room_by_name(db, room)
    if not db_room:
        await websocket.close()
        return

    await manager.connect(websocket, room, nickname)
    
    users = manager.get_users_in_room(room)
    await manager.broadcast({
        "type": "user_list",
        "users": users
    }, room)

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
                    
                    save_message(db, nickname, content, db_room.id, 1, target_nickname)
                    
                    await manager.send_private({
                        "type": "private_message",
                        "nickname": nickname,
                        "target_nickname": target_nickname,
                        "content": private_content,
                        "timestamp": timestamp
                    }, room, target_nickname, nickname)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1111)
