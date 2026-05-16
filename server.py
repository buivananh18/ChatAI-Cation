import os
import asyncio
import websockets
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()

# Biến lưu trữ các client đang kết nối (Dùng cho logic chat của bạn)
# Bạn có thể giữ nguyên hoặc điều chỉnh tùy thuộc vào cấu trúc logic chat hiện tại
connected_clients = set()

# --- HÀM XỬ LÝ LOGIC CHAT (WEBSOCKET HANDLER) ---
async def handle_client(websocket):
    """
    Hàm xử lý kết nối từ Client. 
    Hãy đảm bảo logic nhận/gửi tin nhắn này khớp với thiết kế của bạn.
    """
    print(f"🔌 Có kết nối mới từ: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"📩 Nhận tin nhắn: {message}")
            
            # Logic mẫu: Gửi lại tin nhắn cho tất cả mọi người (Broadcast)
            # Bạn có thể thêm logic lưu tin nhắn vào Database tại đây nếu muốn
            if connected_clients:
                await asyncio.gather(*[client.send(message) for client in connected_clients])
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🛑 Một client đã ngắt kết nối: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

# --- HÀM KHỞI TẠO VÀ ĐẢM BẢO CẤU TRÚC DATABASE ---
def init_database():
    # Lấy chuỗi kết nối từ biến môi trường (.env ở local hoặc Environment trên Render)
    DB_URL = os.environ.get("DATABASE_URL")
    
    if not DB_URL:
        print("❌ [Database] Không tìm thấy DATABASE_URL. Bỏ qua khởi tạo DB.")
        return

    try:
        import psycopg
        
        # Tự động tối ưu hóa SSL dựa trên môi trường chạy
        if "RENDER" in os.environ:
            # Nếu đang chạy TRÊN RENDER: Ép dùng chế độ require bảo mật chuẩn của Linux
            print("🌐 [Database] Phát hiện môi trường Render. Đang kết nối bảo mật nội bộ...")
            conn = psycopg.connect(DB_URL, sslmode="require")
        else:
            # Nếu đang chạy ở MÁY LOCAL: Dùng chuỗi từ file .env của bạn (đã có ?sslmode=no-verify)
            print("💻 [Database] Phát hiện môi trường Local. Đang kết nối tới Render...")
            conn = psycopg.connect(DB_URL)
            
        cursor = conn.cursor()
        
        # Tự động tạo bảng lưu tin nhắn nếu chưa tồn tại
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
        print("⚡ [Database] Kết nối thành công và cấu trúc bảng đã sẵn sàng!")
    except Exception as e:
        print(f"❌ [Database] Lỗi kết nối hoặc khởi tạo dữ liệu: {e}")

# --- HÀM KHỞI CHẠY CHÍNH ---
async def main():
    # 1. Chạy hàm kiểm tra và khởi tạo database trước
    init_database()
    
    # 2. Lấy PORT từ hệ thống (Render tự cấp cổng ngẫu nhiên, local mặc định dùng 8765)
    port = int(os.environ.get("PORT", 8765))
    
    # 3. Kích hoạt Websocket Server chuẩn, lắng nghe ở địa chỉ '0.0.0.0' để mở cổng ra Internet
    async with websockets.serve(handle_client, "0.0.0.0", port):
        print(f"🚀 Server Chat đang chạy an toàn tại cổng {port}...")
        await asyncio.Future()  # Giữ cho server luôn chạy liên tục không bị dừng

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server đã chủ động dừng.")