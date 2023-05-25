import os
import uuid

# import io
import asyncio
# import requests

from typing import Annotated
from pathlib import Path

from fastapi import (
    FastAPI,
    File, 
    UploadFile, 
    Cookie,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException
)
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

from uvicorn import Config, Server

from src.config import WS_SERVER_ROOT
from src.log import logger, error

# from src.video_func import separate_audio, inject_audio
# from src.audio_func import separate_vocals
# from src.transcript import transcribe
# from src.utilities import timed_func

from src.xyz.crawler import get_audio_stream
# from src.webhook import call_webhook

from src.websocket.connection import manager, get_token, ConnectionManager

from templates.Jinja2 import templates

import struct

from celery import Celery

app=FastAPI()

# from gradio_client import Client

# client = Client("abidlabs/music-separation")

# def acapellify(audio_path):
#     # result = client.predict(audio_path, api_name="/predict")
#       return result

# 创建一个Celery实例
celery_app = Celery('worker', broker='pyamqp://guest@localhost//', backend='rpc://')

if not Path("./static"):
    os.makedirs("static")
upload_path = Path("./static/upload")
if not upload_path.exists():
    os.makedirs("static/upload")

# os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# def save_upload_file(upload: UploadFile = File(...)):
#     # 生成文件名
#     filename = str(uuid.uuid1()) + '.' + upload.filename.split(".")[1]
#     # 拼接保存路径 
#     save_path = os.path.join('static/upload', filename) 
#     # 保存文件 
#     with open(save_path, 'wb') as f:
#         # 从SpooledTemporaryFile读取内容并写入
#         for chunk in iter(lambda: upload.file.read(1024 * 1024), b''):  
#             f.write(chunk) 

#     return save_path

async def handle_message(data: bytes, manager: ConnectionManager, token: str, websocket: WebSocket):
    logger.debug(f"【客户端{token}】收到数据长度{len(data)}")
    # Read command
    command = data[0:1].decode('utf-8')
    print(command)
    if command == 'A':
        manager.clear_suspend_msg(token)
        return
    elif command == 'U':
        try:
            # 取文件名以及文件类型的字符长度
            fileName_length, fileType_length = struct.unpack_from('II', data, 1)

            # 获取消息体分片位置
            fileName_start = 9
            fileName_end = fileName_start + fileName_length
            fileType_start = fileName_end
            fileType_end = fileType_start + fileType_length
            fileData_start = fileType_end

            # 获取文件名与文件类型
            fileName = data[fileName_start:fileName_end].decode('utf-8')
            fileType = data[fileType_start:fileType_end].decode('utf-8')

            # 获取文件内容
            fileData = data[fileData_start:]
            logger.debug(f"【客户端{token}】解析数据完成，文件名：{fileName}，文件类型：{fileType}")
        except Exception as e:
            error(f"【客户端{token}】解析数据失败：{str(e)}")
            return

        file_name = str(uuid.uuid1()) + '.' + fileName.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
        logger.debug(f"【客户端{token}】生成文件名：{file_name}")

        # 拼接保存路径 
        save_path = upload_path / file_name

        if not save_path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg', '.mp3', '.m4a', '.wav')):
            error(f"【客户端{token}】上传的不是一个有效格式的文件({fileName})")
            return

        logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(fileData)}")

        with open(str(save_path.resolve()), 'wb') as f:
            f.write(fileData) 
        
        logger.debug(f"【客户端{token}】保存文件成功")

        # # 提取语音文字
        # transcription = transcribe(save_path)

        # 发起后台执行任务
        result = celery_app.send_task('transcribe_task', args=[str(save_path)])
        logger.debug(f"start run task#{result.id}")

        # 启动一个循环，检查任务状态，控制超时时间
        timeout = 600
        while not result.ready():
            if timeout <= 0:
                break
            # 每秒检查一次任务状态
            await asyncio.sleep(1)
            timeout = timeout - 1
        
        if not result.ready():
            logger.debug(f"【客户端{token}】文字提取失败")
            return

        # if transcription is None:
        #     logger.debug(f"【客户端{token}】文字提取失败")
        #     return

        logger.debug(f"【客户端{token}】文字提取成功：\n{str(result.result)}")

        # callback_code = str(uuid.uuid4())
        msg = f'TRA_RETURN:{fileName}的文字提取完成\n{result.result["text_plus_timeline"]}\n===纯文字部分===\n{result.result["text_with_splitter"]}'

        await manager.send_message(msg, websocket)

# websocket接口
@app.websocket("/transcribe")
async def wsworker(websocket: WebSocket, token: Annotated[str, Depends(get_token)]): 
    try:
        await manager.connect(websocket, token)
    except WebSocketDisconnect as e:
        error(f"与客户端建立连接发生异常: {e}")
        manager.disconnect(websocket)

    # callback_code = ""
    while True:
        try:
            data = await websocket.receive_bytes()

            logger.debug(f"收到客户端字节流，长度{len(data)}")

            await handle_message(data, manager, token, websocket)
        # except WebSocketDisconnect as wsd:
        #     error(f"error: {token} disconnected")
        #     manager.disconnect(websocket)
        #     break
        except Exception as e:
            error(f"unexpect error: {e}")
            try:
                if websocket.client_state['is_connected']:
                    await websocket.send_text("TRAN_FAILED")
            finally:
                manager.disconnect(websocket)
            break

@app.get("/transcript/{task_id}")
def get_transcription(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result}

@app.post("/upload")
async def upload_file(upload: UploadFile = File(...)):
    # 生成文件名
    filename = str(uuid.uuid1()) + '.' + upload.filename.split(".")[1]
    # 拼接保存路径 
    save_path = upload_path / filename

    if not save_path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg', '.mp3', '.m4a', '.wav')):
        logger.debug(f"上传的不是一个有效格式的文件({upload.filename})")
        return
    
    # 保存文件 
    with open(save_path, 'wb') as f:
        # 从SpooledTemporaryFile读取内容并写入
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b''):  
            f.write(chunk) 

    logger.debug(f"保存文件成功")

    # 发起后台执行任务
    result = celery_app.send_task('transcribe_task', args=[str(save_path)])
    logger.debug(f"start run task#{result.id}")

    return RedirectResponse(url=f"/transcript/{result.id}", status_code=303)

@app.get("/xyz/getaudio")
def get_xyz_audio(url):
    logger.debug(f"getaudio xyz: {url}")
    # 抓取页面并分析获得音频地址
    audio_urls = get_audio_stream(url)
    if len(audio_urls) == 0:
        return RedirectResponse(url='/', status_code=303)
    return RedirectResponse(url=audio_urls[0], status_code=303)

@app.get("/xyz/download")
def download_xyz_audio(url):
    logger.debug(f"download xyz: {url}")
    # 抓取页面并分析获得音频地址
    stream, ext = get_audio_stream(url)
    if stream is None:
        return RedirectResponse(url='/', status_code=303)
    
    response = StreamingResponse(stream, media_type="application/octet-stream")
    response.headers["Content-Disposition"] = f"attachment; filename={url.split('/')[-1]}.{ext}"

    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "server_root": WS_SERVER_ROOT})


config = Config(app, host='127.0.0.1', port=8000)  
server = Server(config)  

try:   
    server.run()  
except Exception as exc:
    error(f'Server Fatal Error Occurred: {exc}')

