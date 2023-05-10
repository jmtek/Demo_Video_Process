import datetime
import requests

from typing import Annotated
from fastapi import FastAPI, Form
from zhconv import convert

from src.video_func import seperate_audio, inject_audio
from src.audio_func import seperate_vocals
from src.transcript import load_model, transcript

URL_BASE = "http://0.0.0.0/"
FILE_TEMP_DIR = "./static/temp/"

app=FastAPI()

def format_time(num_str):
    return str(datetime.timedelta(seconds=int(num_str)))

def download_file(url):
    # 发送请求
    response = requests.get(url)
    # 获得临时文件名和路径
    file_name = url.split('/')[-1]
    file_path = ''.join([FILE_TEMP_DIR, file_name])

    with open(file_path, 'wb') as f:    
        for chunk in response.iter_content(chunk_size=1024): 
            if chunk:
                f.write(chunk)
    
    return file_path

@app.post("/seperateaudiofromvideo/")
def seperate_audio_from_video(video_url: Annotated[str, Form()]):
    video_path = download_file(video_url)
    audio_path = seperate_audio(video_path)
    return { "url": URL_BASE + audio_path }

@app.post("/removevocal/")
def remove_vocal_from_video(video_url: Annotated[str, Form()]):
    video_path = download_file(video_url)
    old_audio = seperate_audio(video_path)
    voc_audio, no_voc_audio = seperate_vocals(old_audio)
    new_video_path = inject_audio(no_voc_audio, video_path)
    return { "url": URL_BASE + new_video_path }

@app.post("/transcriptfromvideo/")
def transcript_from_video(video_url: Annotated[str, Form()]):
    video_path = download_file(video_url)
    audio = seperate_audio(video_path)
    result = transcript(audio)

    return {
        "text": convert(result["text"],'zh-cn'),
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }

@app.post("/transcriptfromaudio/")
def transcript_from_video(audio_url: Annotated[str, Form()]):
    audio = download_file(audio_url)
    result = transcript(audio)

    return {
        "text": convert(result["text"],'zh-cn'),
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }
