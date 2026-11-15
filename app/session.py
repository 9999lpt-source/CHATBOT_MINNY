# ========== KHAI BAO THU VIEN ==========
import asyncio
import os
import time
import wave
from datetime import datetime

from fastapi import WebSocket

from app import config
from app.protocol import ClientMessage, ClientMsg, State, msg_state

class Session:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.current_turn: int | None = None
        self.active = False

        self._out: asyncio.Queue = asyncio.Queue()
        self._sender_task: asyncio.Task | None = None   #Task của vòng dời Session
        self._turn_task : asyncio.Task | None = None    #Task của luot dang chay

        self._audio = bytearray()                        #Âm thanh của lượt đang thu
        self._start_time = 0.0
        self._last_frame_time = 0.0
        self._watchdog_task: asyncio.Task | None = None
        
    # ========== HÀNG ĐỢI - GỬI TIN ==========
    # ===== VÒNG ĐỜI SESSION =====
    def start(self) -> None:
        self._sender_task = asyncio.create_task(self._sender())
        
    async def close(self) -> None:
        self._stop_watchdog()
        await self._cancel_turn_task()  
        if self._sender_task is not None:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
            self._sender_task = None
            
    # ===== NHẬN DỮ LIỆU TỪ BÊN NGOÀI =====
    def send(self, data: str | bytes) -> None:
        self._out.put_nowait(data)
        
    def _clear_outbox(self) -> None:
        while not self._out.empty():
            self._out.get_nowait()
            
    async def _cancel_turn_task(self) -> None:
        task = self._turn_task
        self._turn_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._clear_outbox()
        
    async def _fake_pipeline(self, turn: int) -> None:
        try:
            self.send(msg_state(turn, State.TRANSCRIBING))
            await asyncio.sleep(3)
            self.send(msg_state(turn, State.THINKING))
            await asyncio.sleep(3)
            print(f"[SESSION] luot {turn} chay xong", flush=True)
        except asyncio.CancelledError:
            print(f"[SESSION] luot {turn} bi huy giua chung", flush=True)
            raise

    # ===== GIÁM SÁT LƯỢT THU ÂM =====
    def _start_watchdog(self, turn: int) -> None:
        self._stop_watchdog()
        self._watchdog_task = asyncio.create_task(self._watchdog(turn))

    def _stop_watchdog(self) -> None:
        task = self._watchdog_task
        self._watchdog_task = None
        if task is not None and not task.done():
            task.cancel()

    async def _watchdog(self, turn: int) -> None:
        while True:
            await asyncio.sleep(config.WATCHDOG_TICK_S)
            now = time.monotonic()
            if now - self._last_frame_time > config.NO_FRAME_TIMEOUT_S:
                await self._abort_audio(turn, "Khong co khung am thanh")
                return
            if now - self._start_time > config.TURN_TIMEOUT_S:
                await self._abort_audio(turn, "qua han cho audio_end")
                return

    async def _abort_audio(self, turn: int, reason: str) -> None:
        if turn != self.current_turn or not self.active:
            return
        self.active = False
        self._audio = bytearray()
        await self._cancel_turn_task()
        print(f"[SESSION] bo luot {turn}: {reason}", flush=True)

    # ===== NHẬN KHUNG ÂM THANH (nhị phân) =====
    async def on_audio_bytes(self, data: bytes) -> None:
        if not self.active:
            return
        if len(self._audio) + len(data) > config.MAX_AUDIO_BYTES:
            self._stop_watchdog()
            await self._abort_audio(self.current_turn, "vuot gioi han dung luong")
            return
        self._audio.extend(data)
        self._last_frame_time = time.monotonic()

    def _save_wav(self, turn: int) -> None:
        try:
            os.makedirs(config.WAV_DIR, exist_ok=True)
            name = f"turn{turn}_{datetime.now().strftime('%H%M%S')}.wav"
            path = os.path.join(config.WAV_DIR, name)
            with wave.open(path, "wb") as f:
                f.setnchannels(config.CHANNELS)
                f.setsampwidth(config.SAMPLE_WIDTH)
                f.setframerate(config.SAMPLE_RATE)
                f.writeframes(bytes(self._audio))
            print(f"[SESSION] da ghi {path}", flush=True)
        except OSError as e:
            print(f"SESSION] ghi WAV loi: {e}", flush=True)
        
    # ===== NƠI DUY NHẤT GỬI ĐẾN WEBSOCKET =====
    async def _sender(self) -> None:
        try:
            while True:
                data = await self._out.get()
                if isinstance(data, bytes):
                    await self.ws.send_bytes(data)
                else:
                    await self.ws.send_text(data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[SESSION] sender loi: {e}", flush=True)
    
    # ========== NHẬN TIN TỪ CLIENT ==========
    # ===== PHÂN LOAI TIN =====
    async def handle_message(self, m: ClientMessage) -> None:
        """Nhận một tin ĐÃ được kiểm tra hợp lệ về định dạng"""
        if m.type == ClientMsg.AUDIO_START:
            await self._on_audio_start(m.turn)
        if m.type == ClientMsg.AUDIO_END:
            self._on_audio_end(m.turn)
        if m.type == ClientMsg.CANCEL:
            await self._on_cancel(m.turn)
            
    # ===== XỬ LÝ TIN audio_start =====
    async def _on_audio_start(self, turn: int) -> None:
        if self.current_turn is not None and turn <= self.current_turn:
            print(f"[SESSION] bo audio_start cu/trung: turn = {turn}", flush=True)
            return
        await self._cancel_turn_task() 
        self.current_turn = turn
        self.active = True
        self._audio = bytearray()
        self._start_time = time.monotonic()
        self._last_frame_time = self._start_time
        self._start_watchdog(turn)
        print(f"[SESSION] bat dau luot {turn}", flush=True)
        self._turn_task = asyncio.create_task(self._fake_pipeline(turn)) 
       
    # ===== XỬ LÝ TIN audio_end ===== 
    def _on_audio_end(self, turn: int) -> None:
        if turn != self.current_turn or not self.active:
            print(f"[SESSION] bo audio_end sai luot: turn = {turn}", flush=True)
            return
        self.active = False
        self._stop_watchdog()
        seconds = len(self._audio) / config.BYTES_PER_SECOND
        print(f"[SESSION] ket thuc luot {turn}: {len(self._audio)} bytes ({seconds:.2f} giay)", flush=True)
        if config.SAVE_WAV:
            self._save_wav(turn)
      
    # ===== XỬ LÝ TIN cancel =====  
    async def _on_cancel(self, turn: int | None = None) -> None:
        if turn is not None and turn != self.current_turn:
            print(f"[SESSION] bo cancel sai luot: turn = {turn}", flush=True)
            return
        if self.current_turn is None:
            return
        await self._cancel_turn_task() 
        self._stop_watchdog()
        self._audio = bytearray()
        self.active = False
        print(f"[SESSION] huy luot {self.current_turn}", flush=True)