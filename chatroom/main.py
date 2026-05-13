from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
from sqlalchemy.orm import Session
import json
from datetime import datetime
import re
import time
import asyncio
from contextlib import asynccontextmanager

from .database import get_db, get_recent_messages, save_message, get_all_rooms, create_room, get_room_by_name, get_private_rooms_for_user
from .message_bus import get_message_bus, MessageBus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化消息总线
    message_bus = await get_message_bus()
    app.state.message_bus = message_bus
    yield
    # 清理资源
    await message_bus.close()


app = FastAPI(title="Real-time Chatroom", lifespan=lifespan)

templates = Jinja2Templates(directory="chatroom/templates")


class ConnectionManager:
    """优化的连接管理器，支持横向扩展"""
    
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
        self.message_bus: MessageBus = None
        self._initialized = False
        self._connection_lock = asyncio.Lock()
        
        # 性能监控
        self.connection_times: Dict[str, float] = {}
    
    async def initialize(self, message_bus: MessageBus):
        """初始化消息总线订阅"""
        if self._initialized:
            return
        
        self.message_bus = message_bus
        
        # 订阅房间消息频道
        async def handle_room_message(data: Dict):
            room = data.get("room")
            if room in self.rooms:
                disconnected_users = []
                for nickname, connection in self.rooms[room].items():
                    try:
                        await connection.send_json(data["message"])
                    except Exception:
                        disconnected_users.append(nickname)
                
                for nickname in disconnected_users:
                    await self.disconnect_internal(room, nickname)
                
                self.message_bus.metrics.messages_broadcast += len(self.rooms[room]) - len(disconnected_users)
        
        # 订阅私信频道
        async def handle_private_message(data: Dict):
            target_nickname = data.get("target_nickname")
            sender_nickname = data.get("sender_nickname")
            message = data.get("message")
            
            for nickname in [target_nickname, sender_nickname]:
                if nickname in self.user_connections:
                    try:
                        await self.user_connections[nickname].send_json(message)
                    except Exception:
                        if nickname in self.user_connections:
                            del self.user_connections[nickname]
                            for room_name, room_users in list(self.rooms.items()):
                                if nickname in room_users:
                                    await self.disconnect_internal(room_name, nickname)
            
            self.message_bus.metrics.private_messages += 1
        
        # 订阅用户列表更新频道
        async def handle_user_list(data: Dict):
            room = data.get("room")
            if room in self.rooms:
                for connection in list(self.rooms[room].values()):
                    try:
                        await connection.send_json({
                            "type": "user_list",
                            "users": list(self.rooms[room].keys())
                        })
                    except Exception:
                        pass
        
        await message_bus.subscribe("room_messages", handle_room_message)
        await message_bus.subscribe("private_messages", handle_private_message)
        await message_bus.subscribe("user_list_updates", handle_user_list)
        
        self._initialized = True
        print("ConnectionManager: Initialized with MessageBus")
    
    async def disconnect_internal(self, room: str, nickname: str):
        """内部断开连接方法"""
        async with self._connection_lock:
            if room in self.rooms and nickname in self.rooms[room]:
                del self.rooms[room][nickname]
                if not self.rooms[room]:
                    del self.rooms[room]
            if nickname in self.user_connections:
                del self.user_connections[nickname]
            
            if nickname in self.connection_times:
                del self.connection_times[nickname]
    
    async def connect(self, websocket: WebSocket, room: str, nickname: str):
        await websocket.accept()
        
        async with self._connection_lock:
            if room not in self.rooms:
                self.rooms[room] = {}
            self.rooms[room][nickname] = websocket
            self.user_connections[nickname] = websocket
            self.connection_times[nickname] = time.time()
            
            if self.message_bus:
                self.message_bus.metrics.connection_count = len(self.user_connections)
    
    async def disconnect(self, websocket: WebSocket, room: str, nickname: str):
        await self.disconnect_internal(room, nickname)
        
        # 广播用户列表更新
        if self.message_bus:
            await self.message_bus.publish("user_list_updates", {
                "room": room,
                "users": self.get_users_in_room(room)
            })
    
    async def broadcast(self, message: dict, room: str):
        """广播消息（通过消息总线支持多实例）"""
        start_time = time.time()
        
        if self.message_bus:
            await self.message_bus.publish_batched("room_messages", {
                "room": room,
                "message": message
            })
        else:
            # 降级到本地广播
            if room in self.rooms:
                disconnected_users = []
                for nickname, connection in self.rooms[room].items():
                    try:
                        await connection.send_json(message)
                    except Exception:
                        disconnected_users.append(nickname)
                
                for nickname in disconnected_users:
                    await self.disconnect_internal(room, nickname)
    
    async def broadcast_to_all(self, message: dict):
        """向所有房间广播"""
        for room in list(self.rooms.keys()):
            await self.broadcast(message, room)
    
    async def send_private_global(self, message: dict, target_nickname: str, sender_nickname: str):
        """发送私信（通过消息总线支持多实例）"""
        if self.message_bus:
            await self.message_bus.publish("private_messages", {
                "target_nickname": target_nickname,
                "sender_nickname": sender_nickname,
                "message": message
            })
        else:
            # 降级到本地发送
            for nickname in [target_nickname, sender_nickname]:
                if nickname in self.user_connections:
                    try:
                        await self.user_connections[nickname].send_json(message)
                    except Exception:
                        if nickname in self.user_connections:
                            del self.user_connections[nickname]
    
    async def send_private(self, message: dict, room: str, target_nickname: str, sender_nickname: str):
        """在房间内发送私信"""
        await self.send_private_global(message, target_nickname, sender_nickname)
    
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
    
    def get_connection_stats(self) -> Dict:
        """获取连接统计信息"""
        now = time.time()
        avg_duration = 0
        if self.connection_times:
            avg_duration = sum(now - t for t in self.connection_times.values()) / len(self.connection_times)
        
        return {
            "total_connections": len(self.user_connections),
            "active_rooms": len(self.rooms),
            "avg_connection_duration_seconds": avg_duration,
            "users_per_room": {room: len(users) for room, users in self.rooms.items()}
        }


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化连接管理器"""
    message_bus = await get_message_bus()
    await manager.initialize(message_bus)


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
    return {"messages": [
        {
            "nickname": m.nickname, 
            "content": m.content, 
            "timestamp": m.timestamp.isoformat(),
            "target_nickname": m.target_nickname
        } for m in messages
    ]}


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


@app.get("/api/stats/performance")
async def get_performance_stats():
    """获取性能指标"""
    message_bus_stats = {}
    if manager.message_bus:
        message_bus_stats = manager.message_bus.get_metrics()
    
    connection_stats = manager.get_connection_stats()
    
    return {
        "message_bus": message_bus_stats,
        "connections": connection_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


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
        await manager.disconnect(websocket, room, nickname)
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
