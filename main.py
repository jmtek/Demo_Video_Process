import os
import uuid

import io
import requests

from typing import Annotated
from pathlib import Path

from fastapi import (
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
from src.log import logger, errlogger

from src.video_func import separate_audio, inject_audio
from src.audio_func import separate_vocals
from src.transcript import transcribe

from src.xyz.crawler import parse_html

from src.websocket.connection import manager, get_token, ConnectionManager

from templates.Jinja2 import templates

from api.index import app

import struct

# from gradio_client import Client

# client = Client("abidlabs/music-separation")

# def acapellify(audio_path):
#     # result = client.predict(audio_path, api_name="/predict")
#       return result

if not Path("./static"):
    os.makedirs("static")
upload_path = Path("./static/upload")
if not upload_path.exists():
    os.makedirs("static/upload")

# os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def save_upload_file(upload: UploadFile = File(...)):
    # 生成文件名
    filename = str(uuid.uuid1()) + '.' + upload.filename.split(".")[1]
    # 拼接保存路径 
    save_path = os.path.join('static/upload', filename) 
    # 保存文件 
    with open(save_path, 'wb') as f:
        # 从SpooledTemporaryFile读取内容并写入
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b''):  
            f.write(chunk) 

    return save_path

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
            errlogger.error(f"【客户端{token}】解析数据失败：{str(e)}")
            return

        file_name = str(uuid.uuid1()) + '.' + fileName.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
        logger.debug(f"【客户端{token}】生成文件名：{file_name}")

        # 拼接保存路径 
        save_path = upload_path / file_name

        if not save_path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg', '.mp3', '.m4a', '.wav')):
            logger.error(f"【客户端{token}】上传的不是一个有效格式的文件({fileName})")
            return

        logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(fileData)}")

        with open(str(save_path.resolve()), 'wb') as f:
            f.write(fileData) 
        
        logger.debug(f"【客户端{token}】保存文件成功")

        # 提取语音文字
        transcription = transcribe(save_path)

        if transcription is None:
            logger.debug(f"【客户端{token}】文字提取失败")
            return

        logger.debug(f"【客户端{token}】文字提取成功：\n{transcription}")

        # callback_code = str(uuid.uuid4())
        msg = f'TRA_RETURN:{fileName}的文字提取完成\n{transcription["text_plus_timeline"]}'

        await manager.send_message(msg, websocket)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "server_root": WS_SERVER_ROOT})

# websocket接口
@app.websocket("/transcribe")
async def worker(websocket: WebSocket, token: Annotated[str, Depends(get_token)]): 
    try:
        await manager.connect(websocket, token)
    except WebSocketDisconnect as e:
        errlogger.error(f"与客户端建立连接发生异常: {e}")
        manager.disconnect(websocket)

    # callback_code = ""
    while True:
        msg = ""
        try:
            data = await websocket.receive_bytes()

            await handle_message(data, manager, token, websocket)

            # singal_text = await websocket.receive_text()

            # if singal_text == "duang":
            #     logger.debug("结束连接")
            #     manager.disconnect(websocket)
            #     return
            
            # if singal_text.startswith("gothca"):
            #     # if callback_code == "":
            #     #   serverside new websocket process
            #     # elif singal_text == f"gothca_{callback_code}":
            #     #   same websocket
            #     manager.clear_suspend_msg(token)
            #     continue
            # elif singal_text.startswith("TRA_UPLOAD:"):
            #     filename = singal_text.split(':')[1]
            #     filename = str(uuid.uuid1()) + '.' + filename.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
            #     logger.debug(f"【客户端{token}】生成文件名：{filename}")

            #     # 拼接保存路径 
            #     save_path = upload_path / filename

            #     if not save_path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg', '.mp3', '.m4a', '.wav')):
            #         logger.error(f"【客户端{token}】上传的不是一个有效格式的文件({singal_text})")
            #         continue

            #     data = await websocket.receive_bytes()

            #     logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(data)}")

            #     # 通知客户端
            #     await websocket.send_text(f"文件传输完成，文件大小为：{len(data)}，开始提取文字")

            #     with open(str(save_path.resolve()), 'wb') as f:
            #         f.write(data) 
                
            #     logger.debug(f"【客户端{token}】保存文件成功")

            #     # await manager.send_message("开始提取文字", websocket)

            #     # 提取语音文字
            #     transcription = transcribe(save_path)

            #     logger.debug(f"【客户端{token}】文字提取成功：\n{transcription}")

            #     # callback_code = str(uuid.uuid4())
            #     msg = f'TRA_RETURN:{singal_text}的文字提取完成\n{transcription["text_plus_timeline"]}'
            #  elif singal_text.startswith("separatevocal:"):
            #     filename = singal_text.split(':')[1]
            #     filename = str(uuid.uuid1()) + '.' + filename.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
            #     logger.debug(f"【客户端{token}】生成文件名：{filename}")

            #     data = await websocket.receive_bytes()

            #     logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(data)}")

            #     # 通知客户端
            #     await websocket.send_text(f"文件传输完成，文件大小为：{len(data)}，开始分离音频")

            #     # 拼接保存路径 
            #     save_path = os.path.join('static/upload', filename) 
            #     with open(save_path, 'wb') as f:
            #         f.write(data) 
                
            #     logger.debug("【客户端{token}】保存文件成功")

            #     # 分离语音和背景音
            #     new_audio = separate_vocals(save_path)

            #     logger.debug(f"【客户端{token}】音频分离成功：\n{new_audio[0]}\n{new_audio[1]}")

            #     # callback_code = str(uuid.uuid4())
            #     msg = f'SEP:{singal_text}的音频分离完成\n{new_audio[0]}\n{new_audio[1]}'

            # if msg != "":
            #     await manager.send_message(msg, websocket)
        except WebSocketDisconnect as wsd:
            errlogger.debug(f"error: {token} disconnected")
            manager.disconnect(websocket)
            break
        except Exception as e:
            errlogger.error(f"unexpect error: {e}")
            try:
                await websocket.send_text("TRAN_FAILED")
            finally:
                manager.disconnect(websocket)
            break

@app.get("/xyz/getaudio")
def get_xyz_audio(url):
    # 抓取页面并分析获得音频地址
    audio_urls = parse_html(url)
    if len(audio_urls) == 0:
        return RedirectResponse(url='/', status_code=303)
    return RedirectResponse(url=audio_urls[0], status_code=303)

@app.get("/xyz/download")
def download_xyz_audio(url):
    # 抓取页面并分析获得音频地址
    audio_urls = parse_html(url)
    if len(audio_urls) == 0:
        return RedirectResponse(url='/', status_code=303)
    
    response = requests.get(audio_urls[0], stream=True)
    response.raise_for_status()

    file_stream = io.BytesIO()
    for chunk in response.iter_content(chunk_size=8192):
        file_stream.write(chunk)
    file_stream.seek(0)
    
    sresponse = StreamingResponse(file_stream, media_type="application/octet-stream")
    sresponse.headers["Content-Disposition"] = f"attachment; filename={url.split('/')[-1]}.{audio_urls[0].split('.')[-1]}"

    return sresponse


config = Config(app, host='127.0.0.1', port=8000)  
server = Server(config)  

try:   
    server.run()  
except Exception as exc:
    logger.error(f'Error occurred: {exc}')

