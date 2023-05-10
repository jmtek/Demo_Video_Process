import whisper

def load_model():
    model = whisper.load_model("small")
    return model

model = load_model()

def transcript(voc_audio):
    audio = whisper.load_audio(voc_audio)
    # audio = whisper.pad_or_trim(audio)

    # mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # _, probs = model.detect_language(mel)

    # options = whisper.DecodingOptions(fp16 = False)
    # result = whisper.decode(model, mel, options)

    # fp16 should be False if use CPU as it is not supported on CPU
    return model.transcribe(audio, verbose=True, fp16 = False)