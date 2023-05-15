import datetime

from typing import Annotated
from fastapi import (
    Cookie,
    Depends,
    WebSocket,
    WebSocketException,
    status,
    Query
)

from src.log import logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[dict] = []

    # async def connect(self, websocket: WebSocket, token: str):
    #     await websocket.accept()
    #     self.active_connections.append({
    #         "token": token,
    #         "connection": websocket,
    #         "pending_msg": "",
    #         "connect_time": datetime.timezone(datetime.timedelta(hours=8))
    #         })
        
    async def connect(self, websocket: WebSocket, token: str):
        logger.debug(f"尝试与客户端{token}建立连接")
        pending_msg = ""
        logger.debug(f"检查当前活跃连接（连接数：{len(self.active_connections)}）")
        for connection in self.active_connections:
            if connection["token"] == token:
                logger.debug("当前客户端存在未结束连接，将关闭原始连接")
                
                pending_msg = connection["pending_msg"]
                self.disconnect(connection["connection"])
                # 这里不做break是为了避免相同token建立过多次连接，从而将相同token的连接都移除，并取最后一个连接的暂存信息进行重发
            
        await websocket.accept()
        logger.debug(f"与客户端{token}连接成功")
        self.active_connections.append({
            "token": token,
            "connection": websocket,
            "pending_msg": "",
            "connect_time": datetime.timezone(datetime.timedelta(hours=8))
            })
        
        if pending_msg != "":
            logger.debug(f"当前客户端{token}之前有未完成消息\n{pending_msg}")
            await manager.send_message(pending_msg, websocket)
            logger.debug(f"向客户端{token}重发消息成功")

    def disconnect(self, websocket: WebSocket):
        for connection in self.active_connections:
            if connection["connection"] is websocket and connection["pending_msg"] == "":   # 有暂存消息未发送则保留该连接
                self.active_connections.remove(connection)
                break

    async def send_message(self, message: str, websocket: WebSocket):
        for connection in self.active_connections:
            if connection["connection"] is websocket:
                this_connection = connection
                this_connection["pending_msg"] = message
                logger.debug(f"【客户端{this_connection['token']}】发送消息前先暂存")
                break

        await websocket.send_text(message)

    def clear_suspend_msg(self, token: str):
        logger.debug(f"收到客户端({token})回调")
        for connection in self.active_connections:
            if connection["token"] == token:
                logger.debug("清空暂存信息")
                connection["pending_msg"] = ""

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection["ws"].send_text(message)

manager = ConnectionManager()

async def get_token(
    websocket: WebSocket,
    # session: Annotated[str | None, Cookie()] = None,
    token: Annotated[str | None, Query()] = None,
):
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return f"{token}"