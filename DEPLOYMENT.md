# ChatAI-Cation

Ứng dụng chat realtime sử dụng WebSocket, aiohttp, và PostgreSQL.

## 🚀 Chạy trên máy Local

### Yêu cầu
- Python 3.8+
- PostgreSQL (tuỳ chọn, nếu dùng database)

### Cài đặt

1. **Clone hoặc tải project**
   ```bash
   cd ChatAI-Cation
   ```

2. **Tạo virtual environment** (tuỳ chọn nhưng khuyến khích)
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # macOS/Linux
   ```

3. **Cài đặt dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Cấu hình .env** (nếu có database)
   ```bash
   cp .env.example .env
   # Sửa .env với DATABASE_URL của bạn
   ```

5. **Chạy server**
   ```bash
   python server.py
   ```

6. **Truy cập**
   - Mở trình duyệt: `http://localhost:8765`
   - WebSocket tự động kết nối: `ws://localhost:8765/ws`

---

## 🌐 Triển khai trên Render

### Bước 1: Push lên GitHub
```bash
git init
git add .
git commit -m "ChatAI-Cation app"
git remote add origin <your-repo-url>
git push -u origin main
```

### Bước 2: Tạo Web Service trên Render
1. Đăng nhập vào [render.com](https://render.com)
2. Click **New +** → **Web Service**
3. Chọn repository của bạn
4. Cấu hình:
   - **Name**: `chatai-cation`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Free Plan** hoặc **Paid Plan** (tuỳ chọn)

### Bước 3: Thêm Environment Variables
Tại mục **Environment**, thêm:
- `DATABASE_URL`: PostgreSQL connection string từ Render (nếu dùng)
- `PORT`: Để trống (Render sẽ tự gán)

### Bước 4: Deploy PostgreSQL (tuỳ chọn)
1. Click **New +** → **PostgreSQL**
2. Cấu hình database
3. Copy connection string vào `DATABASE_URL` env variable của Web Service

### Bước 5: Deploy
- Render sẽ tự động deploy khi bạn push code
- Hoặc click **Manual Deploy** trên dashboard

---

## 📝 File cấu hình Render

- **Procfile**: Hướng dẫn Render cách chạy ứng dụng
- **render.yaml**: Cấu hình tự động triển khai (optional)
- **requirements.txt**: Python dependencies

---

## 🔗 URLs

- **Local**: 
  - HTTP: `http://localhost:8765`
  - WebSocket: `ws://localhost:8765/ws`

- **Production (Render)**:
  - HTTPS: `https://chatai-cation.onrender.com`
  - WebSocket: `wss://chatai-cation.onrender.com/ws`

---

## 🛠️ Troubleshooting

### Lỗi: "Failed to open WebSocket connection"
- Kiểm tra server đang chạy
- Verify WebSocket URL đúng trong browser console

### Lỗi: Database connection refused
- Kiểm tra `DATABASE_URL` chính xác
- PostgreSQL service phải chạy

### Render deployment fails
- Kiểm tra `requirements.txt` có tất cả dependencies
- Xem logs trong Render dashboard

---

## 📦 Dependencies

- **aiohttp**: Web framework async
- **websockets**: WebSocket protocol
- **psycopg**: PostgreSQL adapter
- **python-dotenv**: Environment variables

---

## 🎯 Tính năng

✅ Chat realtime 1:1
✅ WebSocket connection
✅ PostgreSQL integration
✅ Auto-detect local vs Render URLs
✅ Responsive UI

---

**Tác giả**: ChatAI-Cation Team
