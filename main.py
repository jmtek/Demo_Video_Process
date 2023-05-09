import os
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import subprocess
from gradio_client import Client

client = Client("abidlabs/music-separation")

def acapellify(audio_path):
    result = client.predict(audio_path, api_name="/predict")
    return str(result)

def process_video(video_path):
    old_audio = os.path.basename(video_path).split(".")[0] + ".m4a"
    subprocess.run(['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'copy', old_audio])

    new_audio = acapellify(old_audio)

    new_video = f"acap_{video_path}"
    #new_video = os.path.basename(video_path).split(".")[0] + "_new.mp4"
    subprocess.call(['ffmpeg', '-y', '-i', video_path, '-i', new_audio[0], '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', f"static/{new_video}"])
    return new_video


app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

videos = []
audios = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "videos": videos, "audios": audios})

@app.post("/uploadvideo/")
async def upload_video(video: UploadFile = File(...)):
    # 生成文件名
    filename = video.filename
    
    # 拼接保存路径 
    save_path = os.path.join('static', filename) 
    
    # 保存文件 
    with open(save_path, 'wb') as f:
        
        # 从SpooledTemporaryFile读取内容并写入
        for chunk in iter(lambda: video.file.read(1024 * 1024), b''):  
            f.write(chunk)  

    new_video = process_video(save_path)
    videos.append(new_video)
    return RedirectResponse(url='/', status_code=303)


@app.post("/uploadaudio/")
async def upload_audio(audio: UploadFile = File(...)):
    # 生成文件名
    filename = audio.filename
    
    # 拼接保存路径 
    save_path = os.path.join('static', filename) 
    
    # 保存文件 
    with open(save_path, 'wb') as f:
        
        # 从SpooledTemporaryFile读取内容并写入
        for chunk in iter(lambda: audio.file.read(1024 * 1024), b''):  
            f.write(chunk)  
            
    # print(audio.filename)
    new_audio = acapellify(save_path)
    audios.append(new_audio)
    return RedirectResponse(url='/', status_code=303)


