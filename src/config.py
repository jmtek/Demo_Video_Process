import os
import dotenv

dotenv.load_dotenv()

# websocket server root
WS_SERVER_ROOT = os.environ["WS_SERVER_ROOT"] if os.environ.get("WS_SERVER_ROOT") else "127.0.0.1:8000"

# HuggingFace Token
HF_TOKEN = os.environ["HF_TOKEN"] if os.environ.get("HF_TOKEN") else ""

# 如果使用本地Whisper模型，是否输出debug信息
WHISPER_VERBOSE = os.environ.get("WHISPER_VERBOSE") and bool(os.environ["WHISPER_VERBOSE"])

# Whisper使用的模型（base,small,medium,large,large_v2)
WHISPER_MODEL = os.environ["WHISPER_MODEL"] if os.environ.get("WHISPER_MODEL") else "base"

# 基于HF Space的API
TRANS_USE_API = os.environ.get("TRANS_USE_API") and bool(os.environ["TRANS_USE_API"])

# 用DEMUCS分离音频时是否启用内置的FFMPEG自动转换音频
AUDIO_SEP_DOCONVER = os.environ.get("AUDIO_SEP_DOCONVER") and bool(os.environ["AUDIO_SEP_DOCONVER"])

# 使用本地Whisper模型时是否启用GPU加速
TRANS_GPU_ACC = os.environ.get("TRANS_GPU_ACC") and bool(os.environ["TRANS_GPU_ACC"])