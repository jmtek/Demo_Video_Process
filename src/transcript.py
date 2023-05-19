import time

import asyncio, aiohttp

from pathlib import Path

import whisper
# from zhconv import convert
from gradio_client import Client

from src.config import (
    HF_TOKEN, 
    WHISPER_VERBOSE, 
    WHISPER_MODEL,
    TRANS_USE_API, 
    TRANS_GPU_ACC
)
from src.log import logger, error
from src.video_func import separate_audio

def load_model():
    model = whisper.load_model(WHISPER_MODEL)
    return model

SAMPLE_RATE = 16000
CHUNK_LENGTH = 30

if TRANS_USE_API == False:
    model = load_model()

def ping(name):
    url = f'https://huggingface.co/api/telemetry/spaces/jmtek/whisper/{name}'
    print("ping: ", url)

    async def req():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print("pong: ", response.status)
    asyncio.create_task(req())

def format_time(num_str):
    return time.strftime('%H:%M:%S', time.gmtime(int(num_str)))

from src.utilities import timed_func

@timed_func
def decode_by_local_model(voc_audio: str, length: int = CHUNK_LENGTH):
    audio = whisper.load_audio(voc_audio)
    audio = whisper.pad_or_trim(audio, length * SAMPLE_RATE)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    # print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16=TRANS_GPU_ACC, language="zh")
    result = whisper.decode(model, mel, options)

    return result.text

@timed_func
def transcribe(file_path: str):
    # parse file path
    path = Path(file_path)
    # default file type is audio
    video = False
    # convert to audio if input path is a video
    if path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg')):
        video = True

    if TRANS_USE_API:
        # make a ping to wake up remote api if it is sleeping due to inactivity
        ping(f"transcribe_{'video' if video else 'audio'}")
        logger.debug("Transcript use api")
        try:
            client = Client("jmtek/whisper", hf_token=HF_TOKEN)
            return client.predict(str(path.resolve()), api_name="/transcribe_video" if video else "/transcribe_audio")
        except Exception:
            error("HF API返回异常")

    logger.debug("Retry use local model" if TRANS_USE_API else "Transcript use local model")

    try:
        if TRANS_USE_API:
            model = load_model()

        audio = whisper.load_audio(str(path.resolve()))

        # fp16 should be False if use CPU as it is not supported on CPU
        result = model.transcribe(audio, verbose=WHISPER_VERBOSE, fp16 = TRANS_GPU_ACC, language = "zh")

        return {
            "text": result["text"],
            "text_with_splitter": '\n'.join([ f"{segment['text']}" for segment in result["segments"]]),
            #"text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
            "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {segment['text']}" for segment in result["segments"]]),
            "raw": result
        }
    except Exception:
        error("本地Whisper模型处理失败")