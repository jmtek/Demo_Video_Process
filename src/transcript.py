import datetime

import whisper
# from zhconv import convert

def load_model():
    model = whisper.load_model("small")
    return model

model = load_model()

def format_time(num_str):
    return str(datetime.timedelta(seconds=int(num_str)))

from src.utilities import timed_func

@timed_func
def transcript(voc_audio):
    audio = whisper.load_audio(voc_audio)
    # audio = whisper.pad_or_trim(audio)

    # mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # _, probs = model.detect_language(mel)

    # options = whisper.DecodingOptions(fp16 = False)
    # result = whisper.decode(model, mel, options)

    # fp16 should be False if use CPU as it is not supported on CPU
    result = model.transcribe(audio, verbose=True, fp16 = False)

    return {
        "text": result["text"],
        "text_with_splitter": '\n'.join([ f"{segment['text']}" for segment in result["segments"]]),
        # "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {convert(segment['text'], 'zh-cn')}" for segment in result["segments"]])
        "text_plus_timeline": '\n'.join([ f"[{format_time(segment['start'])} --> {format_time(segment['end'])}]  {segment['text']}" for segment in result["segments"]])
        # "raw_transcript": transcript
    }