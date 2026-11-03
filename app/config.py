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

#===== ÂM THANH =====
SAMPLE_RATE = 16000			#Hz
BYTE_PER_SAMPLE = 2			#16-bit
CHANNELS = 1				#mono
BYTES_PER_SECOND = SAMPLE_RATE * BYTE_PER_SAMPLE * CHANNELS

#===== GIỚI HẠN MỖI LƯỢT NÓI=====
MIN_AUDIO_MS = 300
MAX_AUDIO_MS = 15000

MIN_AUDIO_BYTES = BYTES_PER_SECOND * MIN_AUDIO_MS // 1000 #9600
MAX_AUDIO_BYTES = BYTES_PER_SECOND * MAX_AUDIO_MS // 1000 #480000

#===== KIỂM TRA LÚC KHỞI ĐỘNG =====
assert MIN_AUDIO_BYTES < MAX_AUDIO_BYTES, "MIN_AUDIO phải nhỏ hơn MAX_AUDIO"