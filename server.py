import asyncio
import json
import websockets
import os
# Quản lý các kết nối: { username: websocket_object }
clients = {}

# Định nghĩa danh sách Admin cho các kênh 1:N (Ví dụ cấu hình sẵn)
# Kênh "thoi_su" có admin là "admin1"
CHANNELS_ADMIN = {
    "thoi_su": "admin1"
}

async def handle_client(websocket):
    username = None
    try:
        # Bước 1: Đăng ký username khi kết nối
        await websocket.send("HỆ THỐNG: Vui lòng nhập username của bạn:")
        username = await websocket.recv()
        username = username.strip()

        if username in clients or not username:
            await websocket.send("HỆ THỐNG: Username không hợp lệ hoặc đã tồn tại. Đóng kết nối!")
            return

        clients[username] = websocket
        print(f"[+] {username} đã kết nối.")
        await websocket.send(f"HỆ THỐNG: Chào mừng {username}! Bạn đã kết nối thành công.")

        # Bước 2: Lắng nghe và xử lý tin nhắn
        async for message in websocket:
            try:
                data = json.loads(message)
                chat_type = data.get("type")    # "1:1", "1:N", "N:N"
                target = data.get("target")      # Tên người nhận hoặc tên nhóm/kênh
                msg_content = data.get("message")

                # --- CHẾ ĐỘ 1:1 (Chat riêng) ---
                if chat_type == "1:1":
                    if target in clients:
                        payload = json.dumps({"from": username, "type": "1:1", "message": msg_content})
                        await clients[target].send(payload)
                    else:
                        await websocket.send(f"HỆ THỐNG: Không tìm thấy người dùng '{target}'.")

                # --- CHẾ ĐỘ 1:N (Kênh thông báo - Chỉ Admin được nhắn) ---
                elif chat_type == "1:N":
                    if target in CHANNELS_ADMIN:
                        # Kiểm tra xem người gửi có phải Admin của kênh này không
                        if CHANNELS_ADMIN[target] == username:
                            payload = json.dumps({"from": f"📢 [CHANNEL {target}] {username}", "type": "1:N", "message": msg_content})
                            # Gửi cho tất cả mọi người trừ chính admin (hoặc gửi cả admin tùy chọn)
                            for client_name, client_ws in clients.items():
                                if client_name != username:
                                    await client_ws.send(payload)
                        else:
                            await websocket.send(f"HỆ THỐNG LỖI: Bạn không phải Admin của kênh '{target}'. Không thể nhắn tin!")
                    else:
                        await websocket.send(f"HỆ THỐNG: Kênh '{target}' không tồn tại.")

                # --- CHẾ ĐỘ N:N (Phòng chat nhóm - Ai cũng được nhắn) ---
                elif chat_type == "N:N":
                    payload = json.dumps({"from": f"👥 [GROUP {target}] {username}", "type": "N:N", "message": msg_content})
                    # Gửi cho tất cả mọi người trong hệ thống (đơn giản hóa group cho toàn server)
                    for client_name, client_ws in clients.items():
                        if client_name != username:
                            await client_ws.send(payload)

            except json.JSONDecodeError:
                await websocket.send("HỆ THỐNG: Định dạng tin nhắn JSON không hợp lệ.")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Xóa client khi ngắt kết nối
        if username in clients:
            del clients[username]
            print(f"[-] {username} đã ngắt kết nối.")



async def main():
    # Render sẽ cấp port qua biến môi trường 'PORT', nếu không có thì mặc định là 8765
    port = int(os.environ.get("PORT", 8765))
    
    # Cho phép tất cả các IP kết nối bằng cách đổi "localhost" thành "0.0.0.0"
    async with websockets.serve(handle_client, "0.0.0.0", port):
        print(f"🚀 Server Chat đang chạy trên port {port}...")
        await asyncio.Future()
if __name__ == "__main__":
    asyncio.run(main())