from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
from sqlalchemy.orm import Session
import json
from datetime import datetime

from .database import get_db, get_recent_messages, save_message

app = FastAPI(title="Real-time Chatroom")

templates = Jinja2Templates(directory="chatroom/templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def get(request: Request, db: Session = Depends(get_db)):
    messages = get_recent_messages(db)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "messages": messages}
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            nickname = message_data.get("nickname", "Anonymous")
            content = message_data.get("content", "")
            
            if content.strip():
                save_message(db, nickname, content)
                
                timestamp = datetime.utcnow().isoformat()
                await manager.broadcast({
                    "nickname": nickname,
                    "content": content,
                    "timestamp": timestamp
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1111)
