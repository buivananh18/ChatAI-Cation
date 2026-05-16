import asyncio
import json
import os
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
BASE_DIR = Path(__file__).parent

# Biến lưu trữ các client đang kết nối
connected_clients = {}  # {username: websocket}

# --- HÀM XỬ LÝ WEBSOCKET ---
async def websocket_handler(request):
    """
    Hàm xử lý kết nối WebSocket từ Client.
    Sử dụng aiohttp WebSocketResponse thay vì websockets thuần.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    username = None
    print(f"🔌 Có kết nối mới từ: {request.remote}")
    
    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
                
            data = msg.data.strip()
            
            # Nếu chưa có username, dòng đầu tiên là username
            if username is None:
                if not data or data in connected_clients:
                    await ws.send_str(json.dumps({"system": "❌ Username không hợp lệ hoặc đã tồn tại!"}))
                    await ws.close()
                    break
                
                username = data
                connected_clients[username] = ws
                print(f"✅ {username} đã kết nối")
                
                # Broadcast danh sách người dùng online
                online_list = list(connected_clients.keys())
                for user, client_ws in connected_clients.items():
                    if not client_ws.closed:
                        await client_ws.send_str(json.dumps({
                            "system": f"👤 {username} đã tham gia",
                            "online": online_list
                        }))
                continue
            
            print(f"📩 [{username}]: {data}")
            
            # Broadcast tin nhắn cho tất cả người dùng
            broadcast_msg = json.dumps({"from": username, "message": data})
            for user, client_ws in list(connected_clients.items()):
                if not client_ws.closed:
                    await client_ws.send_str(broadcast_msg)
                    
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if username and username in connected_clients:
            del connected_clients[username]
            print(f"🛑 {username} đã ngắt kết nối")
            
            # Broadcast danh sách online sau khi ai đó rời đi
            online_list = list(connected_clients.keys())
            for user, client_ws in connected_clients.items():
                if not client_ws.closed:
                    await client_ws.send_str(json.dumps({
                        "system": f"👤 {username} đã rời khỏi",
                        "online": online_list
                    }))
    
    return ws

# --- HÀM PHỤC VỤ STATIC FILES ---
async def index_handler(request):
    """Phục vụ index.html"""
    return web.FileResponse(BASE_DIR / 'index.html')

async def health_handler(request):
    """Health check endpoint"""
    return web.json_response({'status': 'ok'})

# --- HÀM TẠO ỨNG DỤNG AIOHTTP ---
def create_app():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_static('/static/', path=BASE_DIR, show_index=False)
    return app

# --- HÀM KHỞI TẠO DATABASE ---
def init_database():
    """Khởi tạo bảng chat_messages trên PostgreSQL"""
    if not DB_URL:
        print("❌ [Database] Không tìm thấy DATABASE_URL. Bỏ qua khởi tạo DB.")
        return

    try:
        import psycopg
        
        # Tự động tối ưu hóa SSL dựa trên môi trường chạy
        if "RENDER" in os.environ:
            print("🌐 [Database] Phát hiện môi trường Render. Đang kết nối bảo mật...")
            conn = psycopg.connect(DB_URL, sslmode="require")
        else:
            print("💻 [Database] Phát hiện môi trường Local. Đang kết nối...")
            conn = psycopg.connect(DB_URL)
            
        cursor = conn.cursor()
        
        # Tạo bảng nếu chưa tồn tại
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                sender VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("⚡ [Database] Kết nối thành công!")
    except Exception as e:
        print(f"❌ [Database] Lỗi: {e}")

# --- HÀM KHỞI CHẠY CHÍNH ---
async def main():
    """Khởi chạy server aiohttp"""
    init_database()
    
    port = int(os.environ.get("PORT", 8765))
    app = create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    print(f"🚀 Server Chat đang chạy tại cổng {port}...")
    print(f"📄 Truy cập: http://localhost:{port}")
    print(f"🌐 WebSocket: ws://localhost:{port}/ws")
    
    # Giữ server chạy liên tục
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server đã dừng.")
