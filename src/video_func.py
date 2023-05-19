from pathlib import Path
import subprocess
from src.utilities import timed_func

@timed_func
def separate_audio(video_path: str):
    path = Path(video_path)
    audio_name = path.stem + ".m4a"
    audio_path = path.parent / audio_name
    subprocess.run(['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'copy', audio_path])

    return audio_path

@timed_func
def inject_audio(audio_path: str, video_path: str):
    path = Path(video_path)
    video_filename = path.stem + '_new' + path.suffix()
    new_video = str(path.parent.resolve() / video_filename)
    subprocess.call(['ffmpeg', '-y', '-i', video_path, '-i', audio_path, '-map', '0:v', '-map', '1:a', 
                     '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', new_video])
    return new_video