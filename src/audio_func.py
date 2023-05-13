import os
import subprocess
from src.utilities import timed_func

@timed_func
def separate_vocals(audio_path):
    # result = client.predict(audio_path, api_name="/predict")
    audio_dir = os.path.dirname(audio_path)
    audio_filename = os.path.basename(audio_path).split(".")
    if audio_filename[1] != "wav":
        old_audio_path = audio_path
        audio_path = audio_dir + '/' + audio_filename[0] + '.wav'
        subprocess.run(['ffmpeg',
                        '-i',
                        old_audio_path,
                        audio_path])
        
    subprocess.run(['python3', 
                    '-m', 
                    'demucs.separate', 
                    '-n', 
                    'htdemucs', 
                    '--two-stems=vocals', 
                    '-d', 
                    'cpu', 
                    audio_path, 
                    '-o', 
                    'static'])
    
    output_path = f'static/htdemucs/{audio_filename[0]}/'

    # os.system(f"python3 -m demucs.separate -n htdemucs --two-stems=vocals -d cpu {audio_path} -o out")
    return f"{output_path}vocals.wav",f"{output_path}no_vocals.wav"