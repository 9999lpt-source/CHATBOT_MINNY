# ========== IMPORT CÁC THƯ VIỆN ========== #
import os
from dotenv import load_dotenv

# Tải các biến môi trường trong .env
load_dotenv()

# ===== MẠNG =====
PORT = int(os.environ.get("PORT", "8000"))
HOST = "0.0.0.0"

#===== KHÓA API =====
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ===== ÂM THANH =====
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1
BYTES_PER_SECOND = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS #32000

MAX_AUDIO_BYTES = BYTES_PER_SECOND * 20 # tối đa 20s (firmware 15s)
NO_FRAME_TIMEOUT_S = 6.0                # phải LỚN HƠN thời gian khựng firmware (5s)
TURN_TIMEOUT_S = 25.0                   # từ audio_start đến audio_end
WATCHDOG_TICK_S = 0.5

SAVE_WAV = True
WAV_DIR = "recordings"