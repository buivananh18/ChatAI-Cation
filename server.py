import asyncio
import json
import os
from pathlib import Path
import psycopg
import websockets
from aiohttp import web

DB_URL = os.environ.get("DATABASE_URL")

clients = {}  # {username: websocket}

channels = {
    "thoi_su": {"admin": "admin1", "members": set()},
    "tin_tuc": {"admin": "admin1", "members": set()}
}
groups = {
    "gia_dinh": set(),
    "cong_viec": set(),
    "phong_chat": set()
}

HELP_TEXT = (
    "HỆ THỐNG: Hướng dẫn chat:\n"
    "• Chat 1:1 -> 1:1 @ten_nguoi_nhan : Noi dung\n"
    "• Chat 1:N -> 1:N #ten_kenh : Noi dung (Chỉ Admin có quyền nhắn)\n"
    "• Chat N:N -> N:N #ten_nhom : Noi dung\n"
    "• Tham gia kênh -> subscribe #ten_kenh\n"
    "• Tham gia nhóm -> join #ten_nhom\n"
    "• Kiểm tra danh sách -> list\n"
    "• Voice placeholder -> voice @ten_nguoi_nhan : file.wav\n"
    "• Video placeholder -> video #ten_nhom : video_link"
)

BASE_DIR = Path(__file__).parent


def channel_summary():
    lines = []
    for name, info in channels.items():
        members = ", ".join(sorted(info["members"])) or "(chưa có thành viên)"
        lines.append(f"# {name} (Admin: {info['admin']}): {members}")
    return "\n".join(lines)


def group_summary():
    lines = []
    for name, members in groups.items():
        member_list = ", ".join(sorted(members)) or "(chưa có thành viên)"
        lines.append(f"# {name}: {member_list}")
    return "\n".join(lines)


async def send_system(ws, message, extra=None):
    payload = {"system": message}
    if extra:
        payload.update(extra)
    await ws.send_str(json.dumps(payload))


async def broadcast(payload, recipients, exclude_username=None):
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    for username in recipients:
        if username == exclude_username:
            continue
        ws = clients.get(username)
        if ws:
            await ws.send_str(payload)


async def broadcast_user_list():
    payload = {
        "system": "Cập nhật danh sách người dùng online",
        "online": sorted(clients.keys())
    }
    for ws in clients.values():
        await ws.send_str(json.dumps(payload))


def remove_user_from_rooms(username):
    for channel in channels.values():
        channel["members"].discard(username)
    for members in groups.values():
        members.discard(username)


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    username = None
    try:
        await send_system(ws, "Vui lòng nhập username của bạn:")

        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            content = msg.data.strip()
            if username is None:
                if not content or content in clients:
                    await send_system(ws, "Username không hợp lệ hoặc đã tồn tại. Đóng kết nối!")
                    await ws.close()
                    break

                username = content
                clients[username] = ws
                for channel in channels.values():
                    channel["members"].add(username)
                for group_members in groups.values():
                    group_members.add(username)

                await broadcast_user_list()
                await broadcast({"system": f"Người dùng '{username}' vừa đăng nhập."}, clients.keys(), exclude_username=username)
                print(f"[+] {username} đã kết nối.")
                welcome = (
                    f"Chào mừng {username}! Bạn đã kết nối thành công.\n"
                    "Nhập 'help' để xem hướng dẫn."
                )
                await send_system(ws, welcome)
                await send_system(ws, HELP_TEXT)
                continue

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                await send_system(ws, "Dữ liệu gửi lên phải là JSON hợp lệ.")
                continue

            action = data.get("action", "send")
            if action == "list":
                content_text = (
                    "Danh sách kênh và nhóm hiện có:\n"
                    f"Kênh:\n{channel_summary()}\n"
                    f"Nhóm:\n{group_summary()}\n"
                    f"Người đang online: {', '.join(sorted(clients.keys()))}"
                )
                await send_system(ws, content_text)
                continue

            if action == "help":
                await send_system(ws, HELP_TEXT)
                continue

            if action == "join":
                chat_type = data.get("chat")
                target = data.get("target")
                if chat_type == "channel":
                    if target not in channels:
                        await send_system(ws, f"Kênh '{target}' không tồn tại.")
                        continue
                    channels[target]["members"].add(username)
                    await send_system(ws, f"Bạn đã đăng ký nhận tin kênh '{target}'.")
                    continue
                if chat_type == "group":
                    groups.setdefault(target, set()).add(username)
                    await send_system(ws, f"Bạn đã tham gia nhóm '{target}'.")
                    continue
                await send_system(ws, "Lệnh join không hợp lệ. Dùng 'subscribe #kenh' hoặc 'join #nhom'.")
                continue

            if action == "send":
                chat_type = data.get("type")
                target = data.get("target")
                msg_content = data.get("message", "").strip()
                if not chat_type or not target or not msg_content:
                    await send_system(ws, "Thiếu thông tin gửi tin. Vui lòng kiểm tra lại cú pháp.")
                    continue

                if chat_type == "1:1":
                    if target not in clients:
                        await send_system(ws, f"Người dùng '{target}' hiện không online.")
                        continue
                    payload = {"from": username, "type": "1:1", "message": msg_content}
                    await clients[target].send_str(json.dumps(payload))
                    await send_system(ws, f"Đã gửi tin nhắn tới '{target}'.")
                    continue

                if chat_type == "1:N":
                    if target not in channels:
                        await send_system(ws, f"Kênh '{target}' không tồn tại.")
                        continue
                    if channels[target]["admin"] != username:
                        await send_system(ws, f"Bạn không phải Admin của kênh '{target}'.")
                        continue
                    recipients = channels[target]["members"].copy()
                    if not recipients:
                        await send_system(ws, f"Kênh '{target}' chưa có thành viên nào để nhận tin.")
                        continue
                    payload = {"from": f"📢 [CHANNEL {target}] {username}", "type": "1:N", "message": msg_content}
                    await broadcast(payload, recipients, exclude_username=username)
                    await send_system(ws, f"Đã gửi tin nhắn lên kênh '{target}'.")
                    continue

                if chat_type == "N:N":
                    if target not in groups or username not in groups[target]:
                        await send_system(ws, f"Bạn chưa tham gia nhóm '{target}'. Vui lòng join trước.")
                        continue
                    recipients = groups[target].copy()
                    payload = {"from": f"👥 [GROUP {target}] {username}", "type": "N:N", "message": msg_content}
                    await broadcast(payload, recipients, exclude_username=username)
                    await send_system(ws, f"Đã gửi tin nhắn tới nhóm '{target}'.")
                    continue

                if chat_type in {"voice", "video"}:
                    nested_type = "VOICE" if chat_type == "voice" else "VIDEO"
                    if target.startswith("@"):
                        recipient_name = target[1:]
                        if recipient_name not in clients:
                            await send_system(ws, f"Người dùng '{recipient_name}' hiện không online.")
                            continue
                        payload = {"from": username, "type": nested_type, "message": msg_content}
                        await clients[recipient_name].send_str(json.dumps(payload))
                        await send_system(ws, f"Đã gửi {chat_type} placeholder tới '{recipient_name}'.")
                        continue
                    if target.startswith("#"):
                        room_name = target[1:]
                        if room_name not in groups or username not in groups[room_name]:
                            await send_system(ws, f"Bạn chưa tham gia nhóm '{room_name}'.")
                            continue
                        recipients = groups[room_name].copy()
                        payload = {"from": f"🎥 [{nested_type} {room_name}] {username}", "type": nested_type, "message": msg_content}
                        await broadcast(payload, recipients, exclude_username=username)
                        await send_system(ws, f"Đã gửi {chat_type} placeholder tới nhóm '{room_name}'.")
                        continue
                    await send_system(ws, "Đích voice/video phải là @username hoặc #group.")
                    continue

                await send_system(ws, "Loại chat không hợp lệ. Hãy dùng 1:1, 1:N, N:N, voice, video.")
                continue

            await send_system(ws, "Hành động không được hỗ trợ.")

    except Exception:
        pass
    finally:
        if username:
            remove_user_from_rooms(username)
            if username in clients:
                del clients[username]
            await broadcast_user_list()
            await broadcast({"system": f"Người dùng '{username}' đã ngắt kết nối."}, clients.keys())
            print(f"[-] {username} đã ngắt kết nối.")

    return ws


async def index_handler(request):
    return web.FileResponse(BASE_DIR / 'index.html')


async def health_handler(request):
    return web.json_response({'status': 'ok'})


def create_app():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_static('/static/', path=BASE_DIR, show_index=False)
    return app


# Hàm kết nối và khởi tạo bảng trên Database PostgreSQL (Con voi)
def init_database():
    # Đảm bảo bạn đã lấy biến DB_URL từ file .env ở đầu file server.py nhé:
    # DB_URL = os.environ.get("DATABASE_URL")
    
    if not DB_URL:
        print("❌ [Database] Không tìm thấy DATABASE_URL. Bỏ qua khởi tạo DB.")
        return

    try:
        # Sử dụng thư viện psycopg bản mới mà chúng ta vừa cấu hình
        
        # Thêm tham số sslmode='require' trực tiếp vào code để ép kết nối bảo mật
        conn = psycopg.connect(DB_URL, sslmode='require')
        cursor = conn.cursor()
        
        # Tự động tạo bảng lưu tin nhắn nếu chưa có trên Render
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                sender VARCHAR(50) NOT NULL,
                chat_type VARCHAR(10) NOT NULL,
                target VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("⚡ [Database] Kết nối thành công tới Render và đảm bảo cấu trúc bảng!")
    except Exception as e:
        print(f"❌ [Database] Lỗi kết nối hoặc khởi tạo dữ liệu: {e}")

async def main():
    init_database()  # Gọi hàm ở trên (Bây giờ Python đã hiểu nó là gì)
    
    port = int(os.environ.get("PORT", 8765))
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🚀 Server Chat đang chạy an toàn tại cổng {port}...")
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server đã dừng.")