"""Giả lập ESP32 gửi âm thanh. Chạy: python tools/fake_audio.py [normal|stall|long]"""
import asyncio
import json
import math
import sys

import websockets

URI = "ws://localhost:8000/ws/minny"
RATE = 16000
FRAME_SAMPLES = 320                       # 20 ms
FRAME_SECONDS = FRAME_SAMPLES / RATE


def sine_frame(frame_index: int) -> bytes:
    out = bytearray()
    for i in range(FRAME_SAMPLES):
        n = frame_index * FRAME_SAMPLES + i
        v = int(8000 * math.sin(2 * math.pi * 1000 * n / RATE))
        out += v.to_bytes(2, "little", signed=True)
    return bytes(out)


async def send_audio(ws, seconds: float, paced: bool) -> None:
    for k in range(int(seconds / FRAME_SECONDS)):
        await ws.send(sine_frame(k))
        if paced:
            await asyncio.sleep(FRAME_SECONDS)


async def main(mode: str) -> None:
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps({"type": "audio_start", "turn": 1}))
        if mode == "normal":
            await send_audio(ws, 2.0, paced=True)
            await ws.send(json.dumps({"type": "audio_end", "turn": 1}))
            await asyncio.sleep(7)
        elif mode == "stall":
            await send_audio(ws, 1.0, paced=True)
            await asyncio.sleep(10)
        elif mode == "long":
            await send_audio(ws, 22.0, paced=False)
            await asyncio.sleep(2)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "normal"))