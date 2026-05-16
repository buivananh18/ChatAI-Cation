import asyncio
import websockets
import threading
import json
import sys

async def receive_messages(websocket):
    try:
        async for message in websocket:
            if message.startswith("HỆ THỐNG"):
                print(f"\n{message}")
            else:
                data = json.loads(message)
                print(f"\n[{data['from']}]: {data['message']}")
            print("Nhập tin nhắn (hoặc chat theo cú pháp) > ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n[-] Mất kết nối tới Server.")
        sys.exit()

async def send_messages(websocket):
    username = input()
    await websocket.send(username)

    print("\n--- HƯỚNG DẪN CÚ PHÁP CHAT ---")
    print("• Chat 1:1 ->  1:1 @ten_nguoi_nhan : Noi dung")
    print("• Chat 1:N ->  1:N #ten_kenh : Noi dung (Chỉ Admin)")
    print("• Chat N:N ->  N:N #ten_nhom : Noi dung")
    print("--------------------------------\n")

    while True:
        user_input = await asyncio.to_thread(input, "Nhập tin nhắn > ")
        user_input = user_input.strip()
        
        if not user_input:
            continue

        try:
            parts = user_input.split(":", 1)
            prefix = parts[0].strip().split()
            msg_content = parts[1].strip()

            chat_type = prefix[0]
            target = prefix[1].replace("@", "").replace("#", "")

            payload = {
                "type": chat_type,
                "target": target,
                "message": msg_content
            }
            await websocket.send(json.dumps(payload))

        except Exception:
            print("❌ Sai cú pháp! Ví dụ: '1:1 @phong : chào bạn'")

async def main():
    # ⚠️ THAY ĐƯỜNG DẪN NÀY THÀNH LINK WEBSERVICE RENDER CỦA BẠN (DÙNG wss://)
    # Ví dụ: "wss://chatai-cation.onrender.com"
    uri = "wss://ten-app-cua-ban.onrender.com" 
    
    # Nếu muốn test thử ở máy local trước, bạn có thể đổi lại thành: uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        await asyncio.gather(
            receive_messages(websocket),
            send_messages(websocket)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Đã thoát ứng dụng.")