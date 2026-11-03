import asyncio
import json

import websockets

URL = "ws://localhost:8000/ws/minny"


def j(**kw) -> str:
    return json.dumps(kw)


async def recv_json(ws, timeout: float = 5.0) -> dict:
    """Nhận một tin text và đổi thành dict. Quá hạn thì ném TimeoutError."""
    raw = await asyncio.wait_for(ws.recv(), timeout)
    return json.loads(raw)


async def expect_silence(ws, seconds: float) -> bool:
    """True nếu trong 'seconds' giây KHÔNG nhận được gì."""
    try:
        await asyncio.wait_for(ws.recv(), seconds)
        return False
    except asyncio.TimeoutError:
        return True


def check(name: str, ok: bool) -> None:
    print(f"[{'DAT' if ok else 'SAI'}] {name}")


# ===== KỊCH BẢN 1: một lượt đầy đủ =====
async def scenario_full_turn():
    async with websockets.connect(URL) as ws:
        await ws.send(j(type="audio_start", turn=1))
        m1 = await recv_json(ws)
        m2 = await recv_json(ws)
        check("1. nhan state transcribing",
              m1 == {"type": "state", "turn": 1, "value": "transcribing"})
        check("1. nhan state thinking sau ~3s",
              m2 == {"type": "state", "turn": 1, "value": "thinking"})

# ===== KỊCH BẢN 2: lượt mới đè lượt cũ =====
async def scenario_override():
    async with websockets.connect(URL) as ws:
        await ws.send(j(type="audio_start", turn=1))
        m1 = await recv_json(ws)          # transcribing của lượt 1
        check("2. lượt 1 bắt đầu", m1 is not None and m1["turn"] == 1)

        await ws.send(j(type="audio_start", turn=2))   # đè lên lượt 1
        m2 = await recv_json(ws)
        check("2. nhận state của lượt 2", m2 is not None and m2["turn"] == 2)

        # Chờ quá thời điểm lượt 1 lẽ ra gửi "thinking" (~3s)
        stray = []
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), 4)
                stray.append(json.loads(raw))
        except asyncio.TimeoutError:
            pass
        old = [m for m in stray if m.get("turn") == 1]
        check("2. không có tin lượt 1 lọt ra", len(old) == 0)

# ===== KỊCH BẢN 3: cancel và tin sai =====
async def scenario_cancel_and_bad():
    async with websockets.connect(URL) as ws:
        # 3a: cancel chặn không cho lượt chạy tiếp
        await ws.send(j(type="audio_start", turn=1))
        m = await recv_json(ws)
        check("3a. lượt 1 bắt đầu", m is not None and m["turn"] == 1)

        await ws.send(j(type="cancel"))
        check("3a. sau cancel không có tin nào về", await expect_silence(ws, 4))

        # 3b: tin sai bị từ chối bằng BAD_MESSAGE
        await ws.send("xin chao")
        e1 = await recv_json(ws)
        check("3b. 'xin chao' -> BAD_MESSAGE",
              e1 is not None and e1.get("type") == "error" and e1.get("code") == "BAD_MESSAGE")

        await ws.send(j(type="hello"))
        e2 = await recv_json(ws)
        check("3b. 'hello' -> BAD_MESSAGE",
              e2 is not None and e2.get("code") == "BAD_MESSAGE")

        # kết nối vẫn sống: lượt mới (số lớn hơn lượt đã hủy) chạy bình thường
        await ws.send(j(type="audio_start", turn=2))
        m2 = await recv_json(ws)
        check("3b. sau lỗi vẫn bắt đầu được lượt 2",
              m2 is not None and m2.get("turn") == 2)


async def main():
    await scenario_cancel_and_bad()


if __name__ == "__main__":
    asyncio.run(main())