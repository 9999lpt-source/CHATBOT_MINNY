import asyncio
import websockets

async def test():
    uri = "ws://localhost:8000/ws/minny"
    print(f"Đang kết nối tới {uri}...")
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Da ket noi den server!")
            
                while True:
                    response = await websocket.recv()
                    print(f"[SERVER]: {response}", flush=True)
            
        except websockets.exceptions.ConnectionClosed:
            print("Ngat ket noi", flush=True)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Loi {e}, Thu lai")
            await asyncio.sleep(3)  

if __name__ == "__main__":
    asyncio.run(test())