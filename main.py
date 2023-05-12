import os
import uuid

from fastapi import File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.video_func import seperate_audio, inject_audio
from src.audio_func import seperate_vocals
from src.transcript import transcript
from api.index import app

# from gradio_client import Client

# client = Client("abidlabs/music-separation")

# def acapellify(audio_path):
#     # result = client.predict(audio_path, api_name="/predict")
#     audio_dir = os.path.dirname(audio_path)
#     audio_filename = os.path.basename(audio_path).split(".")
#     if audio_filename[1] != "wav":
#         old_audio_path = audio_path
#         audio_path = audio_dir + '/' + audio_filename[0] + '.wav'
#         subprocess.run(['ffmpeg',
#                         '-i',
#                         old_audio_path,
#                         audio_path])
        
#     subprocess.run(['python3', 
#                     '-m', 
#                     'demucs.separate', 
#                     '-n', 
#                     'htdemucs', 
#                     '--two-stems=vocals', 
#                     '-d', 
#                     'cpu', 
#                     audio_path, 
#                     '-o', 
#                     'static'])
    
#     output_path = f'static/htdemucs/{audio_filename[0]}/'

#     # os.system(f"python3 -m demucs.separate -n htdemucs --two-stems=vocals -d cpu {audio_path} -o out")
#     return f"{output_path}vocals.wav",f"{output_path}no_vocals.wav"

# def process_video(video_path):
#     video_dir = os.path.dirname(video_path)
#     video_filename = os.path.basename(video_path)
#     old_audio = video_dir + '/' + video_filename.split(".")[0] + ".m4a"
#     subprocess.run(['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'copy', old_audio])

#     new_audio = acapellify(old_audio)
#     new_audio_path = os.path.abspath(new_audio[0])

#     new_video = f'{os.path.dirname(video_path)}/{"_new.".join(video_filename.split("."))}'

#     subprocess.call(['ffmpeg', '-y', '-i', video_path, '-i', new_audio_path, '-map', '0:v', '-map', '1:a', 
#                      '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', f"{new_video}"])
#     return new_video


os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
        "home.html", {"request": request, "videos": videos, "audios": audios, "transcriptions": transcriptions})

@app.post("/transcriptaudio/")
async def transcript_audio(audio: UploadFile = File(...)):
    # 保存到本地
    save_path = save_upload_file(audio)
    # 提取语音文字
    transcription = transcript(save_path)

    transcriptions.append(transcription['text_plus_timeline'])
    return RedirectResponse(url='/', status_code=303)

@app.post("/uploadvideo/")
async def upload_video(video: UploadFile = File(...)):
    # 保存到本地
    save_path = save_upload_file(video)
    # 分离音频
    old_audio = seperate_audio(save_path)
    # 分离语音和背景音
    voc_audio, no_voc_audio = seperate_vocals(old_audio)
    # 重新生成新视频
    new_video = inject_audio(no_voc_audio, save_path)

    videos.append(new_video)
    return RedirectResponse(url='/', status_code=303)

@app.post("/uploadaudio/")
async def upload_audio(audio: UploadFile = File(...)):
    # 保存到本地
    save_path = save_upload_file(audio)
    # 分离语音和背景音
    new_audio = seperate_vocals(save_path)

    audios.append(new_audio)
    return RedirectResponse(url='/', status_code=303)
