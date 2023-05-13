import time
import os

import whisper
from zhconv import convert

def load_model():
    model = whisper.load_model("small")
    return model

model = load_model()

ISDEBUG = os.environ.get("WHISPER_DEBUG") and bool(os.environ["WHISPER_DEBUG"])

def format_time(num_str):
    return time.strftime('%H:%M:%S', time.gmtime(int(num_str)))

from src.utilities import timed_func

@timed_func
def transcript(voc_audio: str, length: int = 30):
    audio = whisper.load_audio(voc_audio)
    audio = whisper.pad_or_trim(audio, length)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    # print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16=False, language="zh")
    result = whisper.decode(model, mel, options)

    return result.text

@timed_func
def transcript_with_segments(voc_audio):
    audio = whisper.load_audio(voc_audio)

    # fp16 should be False if use CPU as it is not supported on CPU
    result = model.transcribe(audio, verbose=ISDEBUG if ISDEBUG else False, fp16 = False, language = "zh")

    return {
        "text": result["text"],
        "text_with_splitter": '\n'.join([ f"{segment['text']}" for segment in result["segments"]]),
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        # "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {segment['text']}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }