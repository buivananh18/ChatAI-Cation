import asyncio
import json
import os
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv
from datetime import datetime
import uuid

# Tải cấu hình từ file .env
load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
BASE_DIR = Path(__file__).parent

# Biến lưu trữ các client đang kết nối
connected_clients = {}  # {username: {'ws': websocket, 'groups': [...]}}
groups = {}  # {group_id: {'name': '', 'members': [...], 'created_by': ''}}
call_sessions = {}  # {call_id: {'initiator': '', 'target': '', 'type': 'video|voice', 'status': 'ringing'}}

# --- HÀM GỬI TIN NHẮN ĐẾN USER ---
async def send_to_user(username, message):
    """Gửi tin nhắn cho user cụ thể"""
    if username in connected_clients and not connected_clients[username]['ws'].closed:
        try:
            await connected_clients[username]['ws'].send_str(json.dumps(message))
        except Exception as e:
            print(f"❌ Lỗi gửi tin: {e}")

# --- HÀM BROADCAST ĐẾN TOÀN BỘ ONLINE USERS ---
async def broadcast_to_all(message, exclude_user=None):
    """Broadcast tin nhắn đến tất cả user online"""
    for username, client_data in connected_clients.items():
        if username != exclude_user and not client_data['ws'].closed:
            try:
                await client_data['ws'].send_str(json.dumps(message))
            except Exception:
                pass

# --- HÀM BROADCAST ĐẾN NHÓM ---
async def broadcast_to_group(group_id, message, exclude_user=None):
    """Broadcast tin nhắn đến tất cả member trong nhóm"""
    if group_id in groups:
        for member in groups[group_id]['members']:
            if member != exclude_user and member in connected_clients:
                await send_to_user(member, message)

# --- HÀM LẤY DANH SÁCH ONLINE USERS ---
def get_online_users():
    """Trả về danh sách tất cả user online"""
    return {
        username: {
            'groups': client_data.get('groups', [])
        }
        for username, client_data in connected_clients.items()
    }

# --- HÀM TẠO NHÓM ---
def create_group(group_name, creator, members):
    """Tạo nhóm mới"""
    group_id = str(uuid.uuid4())[:8]
    groups[group_id] = {
        'name': group_name,
        'members': members + [creator],  # Include creator
        'created_by': creator,
        'created_at': datetime.now().isoformat()
    }
    return group_id

# --- HÀM XỬ LÝ WEBSOCKET ---
async def websocket_handler(request):
    """
    Hàm xử lý kết nối WebSocket từ Client.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    username = None
    print(f"🔌 Có kết nối mới từ: {request.remote}")
    
    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            
            try:
                data = json.loads(msg.data)
            except:
                data = {"type": "text", "content": msg.data}
            
            msg_type = data.get('type', 'text')
            
            # === BƯỚC 1: ĐĂNG NHẬP ===
            if msg_type == 'login':
                username = data.get('username', '').strip()
                
                if not username or username in connected_clients:
                    await ws.send_str(json.dumps({
                        "type": "error",
                        "message": "❌ Username không hợp lệ hoặc đã tồn tại!"
                    }))
                    await ws.close()
                    break
                
                # Lưu user
                connected_clients[username] = {
                    'ws': ws,
                    'groups': []
                }
                print(f"✅ {username} đã đăng nhập")
                
                # Gửi danh sách online users
                online_users = get_online_users()
                await send_to_user(username, {
                    "type": "login_success",
                    "username": username,
                    "online_users": online_users
                })
                
                # Broadcast thông báo user mới đăng nhập cho toàn bộ
                await broadcast_to_all({
                    "type": "user_online",
                    "username": username,
                    "online_users": online_users
                }, exclude_user=username)
                
                continue
            
            if not username:
                continue
            
            # === BƯỚC 2: DIRECT MESSAGE (1:1) ===
            if msg_type == 'direct_message':
                target = data.get('target')
                content = data.get('content')
                
                if target in connected_clients:
                    await send_to_user(target, {
                        "type": "direct_message",
                        "from": username,
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Acknowledge for sender
                    await send_to_user(username, {
                        "type": "message_sent",
                        "to": target
                    })
                continue
            
            # === BƯỚC 3: CREATE GROUP ===
            if msg_type == 'create_group':
                group_name = data.get('group_name')
                members = data.get('members', [])  # List of usernames
                
                group_id = create_group(group_name, username, members)
                
                # Add group to all members' list
                connected_clients[username]['groups'].append(group_id)
                for member in members:
                    if member in connected_clients:
                        connected_clients[member]['groups'].append(group_id)
                
                # Notify members about new group
                group_info = groups[group_id]
                await broadcast_to_group(group_id, {
                    "type": "group_created",
                    "group_id": group_id,
                    "group_name": group_name,
                    "members": group_info['members'],
                    "created_by": username
                })
                
                print(f"📁 Nhóm '{group_name}' được tạo bởi {username}")
                continue
            
            # === BƯỚC 4: GROUP MESSAGE ===
            if msg_type == 'group_message':
                group_id = data.get('group_id')
                content = data.get('content')
                
                if group_id in groups:
                    await broadcast_to_group(group_id, {
                        "type": "group_message",
                        "group_id": group_id,
                        "from": username,
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    })
                continue
            
            # === BƯỚC 5: VIDEO/VOICE CALL INITIATE ===
            if msg_type == 'call_initiate':
                target = data.get('target')
                call_type = data.get('call_type')  # 'video' or 'voice'
                group_id = data.get('group_id')  # For group calls
                
                call_id = str(uuid.uuid4())[:8]
                call_sessions[call_id] = {
                    'initiator': username,
                    'target': target,
                    'group_id': group_id,
                    'type': call_type,
                    'status': 'ringing',
                    'created_at': datetime.now().isoformat()
                }
                
                if group_id:
                    # Group call
                    await broadcast_to_group(group_id, {
                        "type": "call_incoming",
                        "call_id": call_id,
                        "initiator": username,
                        "call_type": call_type,
                        "is_group": True
                    })
                else:
                    # 1:1 call
                    if target in connected_clients:
                        await send_to_user(target, {
                            "type": "call_incoming",
                            "call_id": call_id,
                            "initiator": username,
                            "call_type": call_type,
                            "is_group": False
                        })
                
                print(f"📞 {username} gọi {target} ({call_type})")
                continue
            
            # === BƯỚC 6: CALL RESPONSE ===
            if msg_type == 'call_response':
                call_id = data.get('call_id')
                response = data.get('response')  # 'accept' or 'decline'
                
                if call_id in call_sessions:
                    call_data = call_sessions[call_id]
                    
                    if response == 'accept':
                        call_data['status'] = 'active'
                        await send_to_user(call_data['initiator'], {
                            "type": "call_accepted",
                            "call_id": call_id,
                            "target": username
                        })
                    else:
                        await send_to_user(call_data['initiator'], {
                            "type": "call_declined",
                            "call_id": call_id,
                            "reason": "User declined"
                        })
                        del call_sessions[call_id]
                
                continue
            
            # === BƯỚC 7: VOICE MESSAGE ===
            if msg_type == 'voice_message':
                target = data.get('target')
                audio_data = data.get('audio_data')  # Base64 encoded
                duration = data.get('duration')
                group_id = data.get('group_id')
                
                if group_id:
                    await broadcast_to_group(group_id, {
                        "type": "voice_message",
                        "from": username,
                        "audio_data": audio_data,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat()
                    })
                elif target in connected_clients:
                    await send_to_user(target, {
                        "type": "voice_message",
                        "from": username,
                        "audio_data": audio_data,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat()
                    })
                
                print(f"🎙️ {username} gửi voice message")
                continue
            
            # === BƯỚC 8: FILE TRANSFER ===
            if msg_type == 'file_transfer':
                target = data.get('target')
                filename = data.get('filename')
                file_data = data.get('file_data')  # Base64 encoded
                file_size = data.get('file_size')
                group_id = data.get('group_id')
                
                if group_id:
                    await broadcast_to_group(group_id, {
                        "type": "file_transfer",
                        "from": username,
                        "filename": filename,
                        "file_data": file_data,
                        "file_size": file_size,
                        "timestamp": datetime.now().isoformat()
                    })
                elif target in connected_clients:
                    await send_to_user(target, {
                        "type": "file_transfer",
                        "from": username,
                        "filename": filename,
                        "file_data": file_data,
                        "file_size": file_size,
                        "timestamp": datetime.now().isoformat()
                    })
                
                print(f"📁 {username} gửi file: {filename}")
                continue
            
            # === BƯỚC 9: END CALL ===
            if msg_type == 'call_end':
                call_id = data.get('call_id')
                
                if call_id in call_sessions:
                    call_data = call_sessions[call_id]
                    await send_to_user(call_data['initiator'], {
                        "type": "call_ended",
                        "call_id": call_id
                    })
                    if call_data['target']:
                        await send_to_user(call_data['target'], {
                            "type": "call_ended",
                            "call_id": call_id
                        })
                    del call_sessions[call_id]
                
                print(f"📞 {username} kết thúc gọi")
                continue
                    
    except Exception as e:
        print(f"❌ Lỗi WebSocket: {e}")
    finally:
        if username and username in connected_clients:
            del connected_clients[username]
            print(f"🛑 {username} đã ngắt kết nối")
            
            # Broadcast thông báo user offline
            online_users = get_online_users()
            await broadcast_to_all({
                "type": "user_offline",
                "username": username,
                "online_users": online_users
            })
    
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
