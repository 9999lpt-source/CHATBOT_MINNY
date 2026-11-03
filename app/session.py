# ========== KHAI BAO THU VIEN ==========
import asyncio
from fastapi import WebSocket
from app.protocol import ClientMessage, ClientMsg, State, msg_state

class Session:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.current_turn: int | None = None
        self.active = False
        self._out: asyncio.Queue = asyncio.Queue()
        self._sender_task: asyncio.Task | None = None   #Task của vòng dời Session
        self._turn_task : asyncio.Task | None = None    #Task của luot dang chay
        
    # ========== HÀNG ĐỢI - GỬI TIN ==========
    # ===== VÒNG ĐỜI SESSION =====
    def start(self) -> None:
        self._sender_task = asyncio.create_task(self._sender())
        
    async def close(self) -> None:
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
        
    def _clear_outbox(seft) -> None:
        while not seft._out.empty():
            seft._out.get_nowait()
            
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
        print(f"[SESSION] bat dau luot {turn}", flush=True)
        self._turn_task = asyncio.create_task(self._fake_pipeline(turn)) 
       
    # ===== XỬ LÝ TIN audio_end ===== 
    def _on_audio_end(self, turn: int) -> None:
        if turn != self.current_turn or not self.active:
            print(f"[SESSION] bo audio_end sai luot: turn = {turn}", flush=True)
            return
        self.active = False
        print(f"[SESSION] ket thuc luot {turn}", flush=True)
      
    # ===== XỬ LÝ TIN cancel =====  
    async def _on_cancel(self, turn: int | None = None) -> None:
        if turn is not None and turn != self.current_turn:
            print(f"[SESSION] bo cancel sai luot: turn = {turn}", flush=True)
            return
        if self.current_turn is None:
            return
        await self._cancel_turn_task() 
        self.active = False
        print(f"[SESSION] huy luot {self.current_turn}", flush=True)