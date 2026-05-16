import asyncio
import json
import os
import sys
import websockets

async def receive_messages(websocket):
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if "system" in data:
                    print(f"\n{data['system']}")
                    if "online" in data:
                        print("Người dùng online:", ", ".join(data["online"]))
                else:
                    print(f"\n[{data.get('from', 'unknown')}]: {data.get('message', '')}")
            except json.JSONDecodeError:
                print(f"\n{message}")
            print("\nNhập lệnh hoặc tin nhắn > ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n[-] Mất kết nối tới Server.")
        sys.exit()

async def send_messages(websocket):
    username = input("Nhập username: ").strip()
    await websocket.send(username)

    print("\n--- HƯỚNG DẪN CHAT ---")
    print("• Chat 1:1: 1:1 @username : Nội dung")
    print("• Chat 1:N: 1:N #channel : Nội dung (Chỉ Admin)")
    print("• Chat N:N: N:N #group : Nội dung")
    print("• Tham gia kênh: subscribe #channel")
    print("• Tham gia nhóm: join #group")
    print("• Xem danh sách: list")
    print("• Voice placeholder: voice @username : file.wav")
    print("• Video placeholder: video #group : video_link")
    print("• Xem hướng dẫn: help")
    print("--------------------------------\n")

    while True:
        user_input = await asyncio.to_thread(input, "Nhập lệnh hoặc tin nhắn > ")
        user_input = user_input.strip()
        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"help", "h"}:
            print("help: Hiển thị hướng dẫn chat")
            print("list: Xem danh sách người online, kênh, nhóm")
            print("subscribe #channel: Tham gia kênh")
            print("join #group: Tham gia nhóm")
            print("1:1 @username : message")
            print("1:N #channel : message")
            print("N:N #group : message")
            print("voice @username : file.wav")
            print("video #group : video_link")
            continue

        if lowered == "list":
            payload = {"action": "list"}
            await websocket.send(json.dumps(payload))
            continue

        if lowered.startswith("subscribe "):
            parts = user_input.split()
            if len(parts) != 2 or not parts[1].startswith("#"):
                print("❌ Cú pháp sai. Ví dụ: subscribe #thoi_su")
                continue
            payload = {"action": "join", "chat": "channel", "target": parts[1][1:]}
            await websocket.send(json.dumps(payload))
            continue

        if lowered.startswith("join "):
            parts = user_input.split()
            if len(parts) != 2 or not parts[1].startswith("#"):
                print("❌ Cú pháp sai. Ví dụ: join #gia_dinh")
                continue
            payload = {"action": "join", "chat": "group", "target": parts[1][1:]}
            await websocket.send(json.dumps(payload))
            continue

        header, sep, message = user_input.partition(" :")
        if not sep or not message.strip():
            print("❌ Sai cú pháp! Ví dụ: '1:1 @phong : chào bạn'")
            continue

        header_parts = header.split()
        if len(header_parts) < 2:
            print("❌ Sai cú pháp đầu vào. Thiếu loại chat hoặc đích.")
            continue

        chat_type = header_parts[0]
        target = header_parts[1]
        payload_type = chat_type
        if chat_type in {"1:1", "1:N", "N:N", "voice", "video"}:
            payload = {
                "action": "send",
                "type": payload_type,
                "target": target,
                "message": message.strip()
            }
            await websocket.send(json.dumps(payload))
        else:
            print("❌ Loại chat không hỗ trợ. Dùng 1:1, 1:N, N:N, voice, video.")

async def main():
    uri = os.environ.get("CHAT_SERVER", "ws://localhost:8765/ws")
    async with websockets.connect(uri) as websocket:
        await asyncio.gather(receive_messages(websocket), send_messages(websocket))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã thoát ứng dụng.")