from typing import Annotated

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
    Request
)
from fastapi.responses import HTMLResponse
from templates.Jinja2 import templates

from api.index import app

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/wshome", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("wsupload.html", {"request": request})


async def get_cookie_or_token(
    websocket: WebSocket,
    session: Annotated[str | None, Cookie()] = None,
    token: Annotated[str | None, Query()] = None,
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


@app.websocket("/items/{item_id}/ws")
async def websocket_endpoint(
    *,
    websocket: WebSocket,
    item_id: str,
    q: int | None = None,
    cookie_or_token: Annotated[str, Depends(get_cookie_or_token)],
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(
                f"Session cookie or query token value is: {cookie_or_token}"
            )
            if q is not None:
                await websocket.send_text(f"Query parameter q is: {q}")
            await websocket.send_text(f"Message text was: {data}, for item ID: {item_id}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{cookie_or_token} left the chat")

@app.websocket("/wsupload")
async def upload(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            filename = await websocket.receive_text()
            print(f"get upload filename: {filename}")

            data = await websocket.receive_bytes()

            print("get upload data")
            print(f"data length is {len(data)}")

            with open(filename, 'wb') as f:
                f.write(data) 

            print("file saved")

            await websocket.send_text(f"upload done")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Upload close")