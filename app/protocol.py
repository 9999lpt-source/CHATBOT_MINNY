# ========== KHAI BÁO THƯ VIỆN==========
from enum import Enum
import json
from dataclasses import dataclass

# ===== TIN NHẮN ESP32 - SERVER =====
class ClientMsg(str, Enum):
    AUDIO_START = "audio_start"	# bắt đầu 1 lượt nói
    AUDIO_END = "audio_end"   # hết câu nói
    CANCEL = "cancel"			# hủy lượt hiện tại
    
# ===== TIN NHẮN SERVER - ESP32=====
class ServerMsg(str, Enum):
    STATE = "state"				# báo bước đang xử lý (transcribing, thinking...)
    COMMAND = "command"			# lệnh phần cứng (LED...)
    TTS_START = "tts_start"		# sắp gửi PCM
    TTS_END = "tts_end"			# gửi xong PCM
    ERROR = "error"				# có lỗi, kèm mã lỗi
    MUSIC_TITLE = "music_title" # tiêu đề âm nhạc
    
# ===== GIÁ TRỊ CỦA TIN NHẮN "state" =====
class State(str, Enum):
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    
# ===== MÃ LỖI =====
class ErrorCode(str, Enum):
    BAD_MESSAGE = "BAD_MESSAGE"			# tin nhắn sai định dạng
    AUDIO_TOO_SHORT = "AUDIO_TOO_SHORT"	# câu nói quá ngắn
    STT_FAILED = "STT_FAILED"			# STT lỗi hoặc timeout
    STT_EMPTY = "STT_EMPTY"				# Không nhận ra lời nói
    LLM_FAILED = "LLM_FAILED"			# LLM lỗi
    TTS_FAILED = "TTS_FAILED"			# TTS hoặc giải mã lỗi
    MUSIC_NOT_FOUND = "MUSIC_NOT_FOUND"	# Không tìm thấy bài hát
    INTERNAL = "INTERNAL"				#  Lỗi không lường trước
    
# ===== HÀM ĐÓNG GÓI JSON: SERVER - ESP32 =====
def _build(msg_type: ServerMsg, turn : int | None = None, **fields) -> str:
    """"""
    payload = {"type": msg_type.value}
    if turn is not None:
        payload["turn"] = turn
    payload.update(**fields)
    return json.dumps(payload, ensure_ascii=False)

def msg_state(turn: int, value: State) -> str:
    return _build(ServerMsg.STATE, turn, value = value.value)

def msg_command(turn: int, actions: list[str]) -> str:
    return _build(ServerMsg.COMMAND, turn, actions=actions)

def msg_tts_start(turn: int) -> str:
    return _build(ServerMsg.TTS_START, turn)

def msg_tts_end(turn: int) -> str:
    return _build(ServerMsg.TTS_END, turn)

def msg_error(turn: int | None, code: ErrorCode, message: str = "", recoverable: bool = True) -> str:
    return _build(ServerMsg.ERROR, turn, code=code.value, message=message, recoverable=recoverable)

def msg_music_title(turn: int, title: str = "") -> str:
    return _build(ServerMsg.MUSIC_TITLE, turn, title=title)

# ===== PHÂN TÍCH TIN NHẮN TỪ CLIENT =====
class ProtocolError(Exception):
    """"""
    def __init__(self, code: ErrorCode, message: str):
     super().__init__(message)
     self.code = code
     self.message = message
     
@dataclass
class ClientMessage:
    type: ClientMsg
    turn: int | None
    
def parse_client_message(raw: str) -> ClientMessage:
    """"""
    # 1. Tin nhắn phải là json
    try: 
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ProtocolError(ErrorCode.BAD_MESSAGE, "Khong phai json")
        
    # 2. Tin nhắn phải có 'type'
    if not isinstance(data, dict) or "type" not in data:
        raise ProtocolError(ErrorCode.BAD_MESSAGE, "Thieu truong 'type")
    
    # 3. 'type' phải có trong ClientMsg
    try:
        msg_type = ClientMsg(data["type"])
    except ValueError:
        raise ProtocolError(ErrorCode.BAD_MESSAGE, f"Loai tin la: {data['type']}")
    
    # 4. 'turn' phải là số nguyên
    turn = data.get("turn")
    if turn is not None and (not isinstance(turn, int) or isinstance(turn, bool)):
        raise ProtocolError(ErrorCode.BAD_MESSAGE, "'turn' phai la so nguyen")
    
    # 5. 'AUDIO_START' và 'AUDIO_END' bắt buộc phải có 'turn' đi kèm
    if msg_type in (ClientMsg.AUDIO_START, ClientMsg.AUDIO_END) and turn is None:
        raise ProtocolError(ErrorCode.BAD_MESSAGE, f"'{msg_type.value}' can co 'turn'")
    
    return ClientMessage(type=msg_type, turn=turn)