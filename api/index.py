import datetime
import uuid
import aiofiles
import aiohttp

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

async def download_file(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # 文件名
                file_name = url.split('/')[-1]  
                file_name = FILE_TEMP_DIR + str(uuid.uuid1()) + '.' + file_name.split(".")[1]        
                
                async with aiofiles.open(file_name, 'wb') as f: 
                    async for chunk in response.content.iter_chunked(1024):  
                        if chunk:
                            f.write(chunk)  
                            
        return file_name
    except Exception as e:
        # return {"status": "error", "error": str(e)}
        return ""

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
async def transcript_from_video(video_url: Annotated[str, Form()]):
    video_path = await download_file(video_url)
    audio = seperate_audio(video_path)
    result = transcript(audio)

    return {
        "text": convert(result["text"],'zh-cn'),
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }

@app.post("/transcriptfromaudio/")
async def transcript_from_video(audio_url: Annotated[str, Form()]):
    audio = await download_file(audio_url)
    result = transcript(audio)

    return {
        "text": convert(result["text"],'zh-cn'),
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }
