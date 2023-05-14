import os
import uuid

from fastapi import (
    File, 
    UploadFile, 
    Request,
    WebSocket,
    WebSocketDisconnect
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

from uvicorn import Config, Server

from src.log import logger
from src.video_func import separate_audio, inject_audio
from src.audio_func import separate_vocals
from src.transcript import transcript_with_segments

from src.websocket.connection import manager

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
async def home(request: Request):
    transcription = None if len(transcriptions) == 0 else transcriptions[len(transcriptions)-1:][0]
    return templates.TemplateResponse(
        "transcript.html", {"request": request, "server_root": SERVER_ROOT})

@app.websocket("/transcript/upload")
async def transcript_audio(websocket: WebSocket): 
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            if data == "duang":
                logger.debug("结束连接")
                manager.disconnect(websocket)
                return
            
            filename = str(uuid.uuid1()) + '.' + data.split(".")[-1:][0] # [-1:]防止文件名带'.'，取split之后数组的最后一个元素
            logger.debug(f"生成文件名：{filename}")

            data = await websocket.receive_bytes()

            logger.debug(f"收到文件流，文件大小为：{len(data)}")

            with open(filename, 'wb') as f:
                f.write(data) 
            
            logger.debug("保存文件成功")

            # 提取语音文字
            transcription = transcript_with_segments(filename)

            logger.debug(f"文字提取成功：\n{transcription}")

            await websocket.send_text(transcription["text_plus_timeline"])
    except WebSocketDisconnect as wse:
        logger.error(f"websocket error: {wse}")
        manager.disconnect(websocket)

# 将视频的人声去除
@app.get("/removevocal/upload", response_class=HTMLResponse)
async def home(request: Request):
    video = None if len(videos) == 0 else videos[len(videos)-1:][0]
    return templates.TemplateResponse(
        "video.html", {"request": request, "video": video})

@app.post("/removevocal/upload")
async def upload_video(video: UploadFile = File(...)):
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
@app.get("/separatevocals/upload", response_class=HTMLResponse)
async def home(request: Request):
    audio = None if len(audios) == 0 else audios[len(audios)-1:][0]
    return templates.TemplateResponse(
        "audio.html", {"request": request, "audio": audio})

@app.post("/separatevocals/upload")
async def upload_audio(audio: UploadFile = File(...)):
    # 保存到本地
    save_path = save_upload_file(audio)
    # 分离语音和背景音
    new_audio = separate_vocals(save_path)

    audios.append(new_audio)
    return RedirectResponse(url='/separatevocals/upload', status_code=303)


config = Config(app, host='127.0.0.1', port=8000)  
server = Server(config)  

try:   
    server.run()  
except Exception as exc:
    logger.error(f'Error occurred: {exc}')
