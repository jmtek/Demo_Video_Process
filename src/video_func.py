import os
import subprocess
from src.utilities import timed_func

@timed_func
def separate_audio(video_path: str):
    video_dir = os.path.dirname(video_path)
    video_filename = os.path.basename(video_path)
    old_audio = video_dir + '/' + video_filename.split(".")[0] + ".m4a"
    subprocess.run(['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'copy', old_audio])

    return old_audio

@timed_func
def inject_audio(audio_path: str, video_path: str):
    video_filename = os.path.basename(video_path)
    new_video = f'{os.path.dirname(video_path)}/{"_new.".join(video_filename.split("."))}'
    subprocess.call(['ffmpeg', '-y', '-i', video_path, '-i', audio_path, '-map', '0:v', '-map', '1:a', 
                     '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', f"{new_video}"])
    return new_video