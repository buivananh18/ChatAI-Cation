import asyncio
import websockets
import threading
import json
import sys

# Luồng lắng nghe tin nhắn từ Server gửi về
async def receive_messages(websocket):
    try:
        async for message in websocket:
            # Kiểm tra nếu là tin nhắn hệ thống (dạng text thuần)
            if message.startswith("HỆ THỐNG"):
                print(f"\n{message}")
            else:
                # Nếu là tin nhắn từ người dùng khác (dạng JSON)
                data = json.loads(message)
                print(f"\n[{data['from']}]: {data['message']}")
            print("Nhập tin nhắn (hoặc chat theo cú pháp) > ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n[-] Mất kết nối tới Server.")
        sys.exit()

# Luồng gửi tin nhắn lên Server
async def send_messages(websocket):
    # Nhập username đầu tiên
    username = input()
    await websocket.send(username)

    print("\n--- HƯỚNG DẪN CÚ PHÁP CHAT ---")
    print("• Chat 1:1 ->  1:1 @ten_nguoi_nhan : Noi dung tin nhan")
    print("• Chat 1:N ->  1:N #ten_kenh : Noi dung tin nhan (Chỉ dành cho Admin)")
    print("• Chat N:N ->  N:N #ten_nhom : Noi dung tin nhan")
    print("--------------------------------\n")

    while True:
        user_input = await asyncio.to_thread(input, "Nhập tin nhắn > ")
        user_input = user_input.strip()
        
        if not user_input:
            continue

        try:
            # Phân tách cú pháp: [Loại] [Mục tiêu] : [Tin nhắn]
            # Ví dụ: 1:1 @an : hello
            parts = user_input.split(":", 1)
            prefix = parts[0].strip().split()
            msg_content = parts[1].strip()

            chat_type = prefix[0] # "1:1", "1:N", "N:N"
            target = prefix[1].replace("@", "").replace("#", "") # Xóa ký tự @ hoặc # đi

            payload = {
                "type": chat_type,
                "target": target,
                "message": msg_content
            }
            await websocket.send(json.dumps(payload))

        except Exception:
            print("❌ Sai cú pháp! Vui lòng nhập lại đúng định dạng ví dụ: '1:1 @phong : chào bạn'")

async def main():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Chạy song song luồng gửi và luồng nhận
        await asyncio.gather(
            receive_messages(websocket),
            send_messages(websocket)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Đã thoát ứng dụng.")