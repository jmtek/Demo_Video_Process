import os,datetime
import uuid
import aiofiles
import aiohttp

from typing import Annotated
from fastapi import FastAPI, Form
from zhconv import convert

from src.video_func import seperate_audio, inject_audio
from src.audio_func import seperate_vocals
from src.transcript import transcript
from src.utilities import timed_func

URL_BASE = "http://0.0.0.0/"
FILE_TEMP_DIR = "./static/temp/"

app=FastAPI()

def format_time(num_str):
    return str(datetime.timedelta(seconds=int(num_str)))

@timed_func
async def download_file(url):
    # 文件名
    file_name = url.split('/')[-1]  
    file_name = FILE_TEMP_DIR + str(uuid.uuid1()) + '.' + file_name.split(".")[1]  
    """异步下载文件并保存"""
    try: 
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # 确认响应状态码为200
                assert response.status == 200 
                
                # 获取文件总大小
                file_size = int(response.headers.get('Content-Length'))
                
                # 已下载大小
                downloaded = 0  
                
                # 下载文件并写入
                async with aiofiles.open(file_name, 'wb') as f:
                    while True:
                        # 读取chunk大小数据
                        chunk = await response.content.read(1024)  
                        if not chunk:
                            break
                        # 写入文件
                        await f.write(chunk)             
                        # 更新已下载大小
                        downloaded += len(chunk)
                        print(f'{downloaded}/{file_size}') 
                        
    except Exception as e:
        print(e)
        # 如果下载失败,删除空文件
        os.remove(file_name)
        file_name = ""

    return file_name
    
def bad_request_response(message: str, exception: Exception):
    return {
        "code": 500,
        "message": message,
        "exception": exception
    }

def good_request_response(result, **kwargs):
    return {
        "code": 200,
        "result": result
    }

@app.post("/seperateaudiofromvideo/")
async def seperate_audio_from_video(video_url: Annotated[str, Form()]):
    video_path = await download_file(video_url)
    if video_path == "":
        return bad_request_response("download video from url failed")
    try:
        audio_path = seperate_audio(video_path)
    except Exception as e:
        return bad_request_response("分离音频失败", e)
    finally:
        os.remove(video_path)
    return good_request_response({ "url": URL_BASE + audio_path })

@app.post("/removevocal/")
async def remove_vocal_from_video(video_url: Annotated[str, Form()]):
    video_path = await download_file(video_url)
    if video_path == "":
        return bad_request_response("download video from url failed")
    try:
        old_audio = seperate_audio(video_path)
        voc_audio, no_voc_audio = seperate_vocals(old_audio)
        os.remove(old_audio)
        new_video_path = inject_audio(no_voc_audio, video_path)
        os.remove(voc_audio)
        os.remove(no_voc_audio)
    except Exception as e:
        return bad_request_response("视频处理失败", e)
    finally:
        os.remove(video_path)

    return good_request_response({ "url": URL_BASE + new_video_path })

@app.post("/transcriptfromvideo/")
async def transcript_from_video(video_url: Annotated[str, Form()]):
    video_path = await download_file(video_url)
    if video_path == "":
        return bad_request_response("download video from url failed")
    try:
        audio = seperate_audio(video_path)
        result = transcript(audio)
        os.remove(audio)
    except Exception as e:
        return bad_request_response("视频转文字失败", e)
    finally:
        os.remove(video_path)

    return good_request_response({
        "text": result["text"],
        # "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {segment['text']}" for segment in result["segments"]])
        # "raw_transcript": transcript
    })

@app.post("/transcriptfromaudio/")
async def transcript_from_video(audio_url: Annotated[str, Form()]):
    audio = await download_file(audio_url)
    if audio == "":
        return bad_request_response("download audio from url failed")
    try:
        result = transcript(audio)
    except Exception as e:
        return bad_request_response("音频转文字失败", e)
    finally:
        os.remove(audio)

    return good_request_response({
        "text": result["text"],
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {segment['text']}" for segment in result["segments"]])
        # "raw_transcript": transcript
    })
