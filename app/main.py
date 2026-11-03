# ========== IMPORT CÁC THƯ VIỆN ========== #
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app import config
from app.protocol import ProtocolError, msg_error, parse_client_message
from app.session import Session

# Khởi tạo FastAPI
app = FastAPI()

# ========== ENDPOINT KIỂM TRA NHANH SERVER ========== #
@app.get('/health')
def health():
    """KIỂM TRA SỨC KHỎE CỦA SERVER"""
    return {"status":"ok"}

# ========== ENDPOINT WEBSOCKET CHÍNH ========== #
@app.websocket("/ws/minny")
async def ws_minny(ws: WebSocket):
    """HÀM WEBSOCKET CHÍNH - LẮNG NGHE SỰ KIỆN - PHẢN HỒI ESP32"""
    
    # Chấp nhận kết nối ws từ esp32
    await ws.accept()
    session = Session(ws)
    session.start()
    print("[MAIN]: ESP32 DA KET NOI", flush=True)
    
    try:
        # Liên tục lắng nghe từ Esp32
        while True:
            # Nhận tin từ Esp32 (text hoặc bytes)
            msg = await ws.receive()
            
            # Nếu mất kết nối -> thoát
            if msg["type"] == "websocket.disconnect":
                break
            
            # Nếu là text
            if msg.get("text") is not None:
                
                # 1. Đọc
                text_data = msg["text"]
                
                # 2. Kiểm tra
                try:
                    # Nếu hợp lệ
                    client_message = parse_client_message(text_data)
                except ProtocolError as e:
                    # Nếu không hợp lệ
                    print(f"[MAIN] tin sai: {e.message}", flush=True)
                    session.send(msg_error(None, e.code, e.message))
                    continue

                # 3. Gửi tin nhắn đi xử lý
                await session.handle_message(client_message)
                
            # Nếu là bytes
            elif msg.get("bytes") is not None:
                bytes_data = msg["bytes"]
                print(f"[MAIN] len_byte: {len(bytes_data)}", flush=True)
    
    # Mất kết nối đột ngột
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()
        print("[MAIN] ESP32 ngat ket noi", flush=True)