import os
import uuid

from typing import Annotated

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
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

from uvicorn import Config, Server

from src.log import logger
from src.video_func import separate_audio, inject_audio
from src.audio_func import separate_vocals
from src.transcript import transcript_with_segments

from src.websocket.connection import manager, get_token

from templates.Jinja2 import templates

from api.index import app

# from gradio_client import Client

# client = Client("abidlabs/music-separation")

# def acapellify(audio_path):
#     # result = client.predict(audio_path, api_name="/predict")
#       return result

SERVER_ROOT = os.environ["SERVER_ROOT"] if os.environ.get("SERVER_ROOT") else "127.0.0.1:8000"

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

videos = []
audios = []
transcriptions = []

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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request})

@app.get("/read", response_class=HTMLResponse)
async def checkall(request: Request):
    return templates.TemplateResponse(
        "read.html", {
            "request": request, 
            "videos": videos, 
            "audios": audios,
            "transcriptions": transcriptions
            })

# 人声转文字
@app.get("/transcript/upload", response_class=HTMLResponse)
async def transcript_audio(request: Request):
    return templates.TemplateResponse(
        "transcript.html", {"request": request, "server_root": SERVER_ROOT})

# 人声转文字 websocket接口
@app.websocket("/transcript/upload")
async def transcript_audio(websocket: WebSocket, token: Annotated[str, Depends(get_token)]): 
    try:
        await manager.connect(websocket, token)
    except WebSocketDisconnect as e:
        logger.error(f"与客户端建立连接发生异常: {e}")
        manager.disconnect(websocket)

    callback_code = ""
    while True:
        try:
            singal_text = await websocket.receive_text()

            if singal_text == "duang":
                logger.debug("结束连接")
                manager.disconnect(websocket)
                return
            
            if singal_text.startswith("gothca"):
                # if callback_code == "":
                #   serverside new websocket process
                # elif singal_text == f"gothca_{callback_code}":
                #   same websocket
                manager.clear_suspend_msg(token)
            else:    
                filename = str(uuid.uuid1()) + '.' + singal_text.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
                logger.debug(f"【客户端{token}】生成文件名：{filename}")

                data = await websocket.receive_bytes()

                logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(data)}")

                # 拼接保存路径 
                save_path = os.path.join('static/upload', filename) 
                with open(save_path, 'wb') as f:
                    f.write(data) 
                
                logger.debug("【客户端{token}】保存文件成功")

                # await manager.send_message("开始提取文字", websocket)

                # 提取语音文字
                transcription = transcript_with_segments(save_path)

                logger.debug(f"【客户端{token}】文字提取成功：\n{transcription}")

                # callback_code = str(uuid.uuid4())
                msg = f'{singal_text}的文字提取完成\n{transcription["text_plus_timeline"]}'

                await manager.send_message(msg, websocket)
        except WebSocketDisconnect as wsd:
            logger.debug(f"error: {token} disconnected")
            manager.disconnect(websocket)
            break
        except Exception as e:
            logger.error(f"unexpect error: {e}")
            manager.disconnect(websocket)
            break

# 将视频的人声去除
@app.get("/removevocal/upload", response_class=HTMLResponse)
async def removevoal(request: Request):
    video = None if len(videos) == 0 else videos[len(videos)-1:][0]
    return templates.TemplateResponse(
        "video.html", {"request": request, "video": video})

@app.post("/removevocal/upload")
async def removevoal(video: UploadFile = File(...)):
    # 保存到本地
    save_path = save_upload_file(video)
    # 分离音频
    old_audio = separate_audio(save_path)
    # 分离语音和背景音
    voc_audio, no_voc_audio = separate_vocals(old_audio)
    # 重新生成新视频
    new_video = inject_audio(no_voc_audio, save_path)

    videos.append(new_video)
    return RedirectResponse(url='/removevocal/upload', status_code=303)

# 音频分离，提取人声部分和背景音
@app.get("/separatevocal/upload", response_class=HTMLResponse)
async def separatevocal(request: Request):
    return templates.TemplateResponse(
        "audio.html", {"request": request, "server_root": SERVER_ROOT})

# 音频分离，提取人声部分和背景音 websocket接口
@app.websocket("/separatevocal/upload")
async def separatevocal(websocket: WebSocket, token: str): 
    try:
        await manager.connect(websocket, token)
    except WebSocketDisconnect as e:
        logger.error(f"与客户端建立连接发生异常: {e}")
        manager.disconnect(websocket)

    callback_code = ""
    while True:
        try:
            singal_text = await websocket.receive_text()

            if singal_text == "duang":
                logger.debug("结束连接")
                manager.disconnect(websocket)
                return
            
            if singal_text.startswith("gothca"):
                # if callback_code == "":
                #   serverside new websocket process
                # elif singal_text == f"gothca_{callback_code}":
                #   same websocket
                manager.clear_suspend_msg(token)
            else:    
                filename = str(uuid.uuid1()) + '.' + singal_text.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
                logger.debug(f"【客户端{token}】生成文件名：{filename}")

                data = await websocket.receive_bytes()

                logger.debug(f"【客户端{token}】收到文件流，文件大小为：{len(data)}")

                # 拼接保存路径 
                save_path = os.path.join('static/upload', filename) 
                with open(save_path, 'wb') as f:
                    f.write(data) 
                
                logger.debug("【客户端{token}】保存文件成功")

                # await manager.send_message("开始提取文字", websocket)

                # 分离语音和背景音
                new_audio = separate_vocals(save_path)

                logger.debug(f"【客户端{token}】音频分离成功：\n../{new_audio[0]}\n../{new_audio[1]}")

                # callback_code = str(uuid.uuid4())
                msg = f'{singal_text}的音频分离完成\n../{new_audio[0]}\n../{new_audio[1]}'

                await manager.send_message(msg, websocket)
        except WebSocketDisconnect as wsd:
            logger.debug(f"error: {token} disconnected")
            manager.disconnect(websocket)
            break
        except Exception as e:
            logger.error(f"unexpect error: {e}")
            manager.disconnect(websocket)
            break

config = Config(app, host='127.0.0.1', port=8000)  
server = Server(config)  

try:   
    server.run()  
except Exception as exc:
    logger.error(f'Error occurred: {exc}')
