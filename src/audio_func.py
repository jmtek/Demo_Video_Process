import subprocess
from pathlib import Path
from demucs import separate
from src.utilities import timed_func
from src.config import AUDIO_SEP_DOCONVER
from src.video_func import separate_audio

VOCAL_FILENAME = "vocals.mp3"
DRUMS_FILENAME = "drums.mp3"
BASS_FILENAME = "bass.mp3"
OTHER_FILENAME = "other.mp3"
NO_VOCAL_FILENAME = "no_vocals.mp3"

@timed_func
def separate_vocals(
    file_path: str,
    two_stems: bool = True,
    stem_to_separate: str = "vocals", # 只分离人声和其他（另外支持drums、bass、guitar以及piano，piano效果一般）
    model: str = "htdemucs"
    ):
    # parse file path
    path = Path(file_path)
    # filename as trackname
    trackname = path.stem
    # convert to audio if input path is a video
    if path.name.lower().endswith(('.mp4', '.avi', '.wmv', '.mov', '.flv', '.mpeg')):
        path = Path(separate_audio(file_path))

    if AUDIO_SEP_DOCONVER and path.suffix.lower() != ".wav":
        new_audio_path = str(path.parent.resolve()) + '/' + trackname + '.wav'
        subprocess.run(['ffmpeg', '-i', str(path.resolve()), new_audio_path])
        path = Path(new_audio_path)
    
    # os.system(f"python3 -m demucs.separate -n htdemucs --two-stems=vocals -d cpu {audio_path} -o out")
    params = []
    # 输出 mp3 (默认 wav)
    params.append("--mp3")
    # 是否只分离一个内容（人声、鼓声、贝斯声等等）
    if two_stems:
        params.append(f"--two-stems={stem_to_separate}")
    # 模型
    params.append(f"-n={model}")
    # 需要分离的音频文件路径
    params.append(str(path.resolve()))
    # 输出的主目录
    params.append("-o=static")

    # 调用FB DEMUCS执行分离
    separate.main(params)
    
    output_path = Path("./static") / model / trackname

    if not two_stems:
        return str(output_path / VOCAL_FILENAME), str(output_path / DRUMS_FILENAME), str(output_path / BASS_FILENAME), str(output_path / OTHER_FILENAME)

    output_file = stem_to_separate + ".mp3"
    return str(output_path / output_file)