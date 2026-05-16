# ChatAI-Cation

Ứng dụng chat Python cho các kịch bản:
- Chat 1:1 (riêng tư)
- Chat 1:N (kênh chỉ Admin được gửi tin)
- Chat N:N (nhóm chat mọi thành viên tương tác)
- Placeholder nâng cao cho voice/video

## Cài đặt

1. Cài Python 3.10+.
2. Cài thư viện:
   ```bash
   pip install -r requirements.txt
   ```

## Chạy server

```bash
python server.py
```

Server mặc định chạy trên `ws://localhost:8765`.

Khi chạy server, bạn có thể mở trình duyệt tới `http://localhost:8765` để dùng giao diện web.

### Chạy trên Render

1. Tạo Web Service mới trên Render.
2. Chọn môi trường Python và thiết lập command khởi động là:
   ```bash
   python server.py
   ```
3. Render sẽ cung cấp cổng bằng biến `PORT`.
4. Với client terminal, đặt `CHAT_SERVER` thành đường dẫn WebSocket của Render, ví dụ:
   ```bash
   set CHAT_SERVER=wss://your-app.onrender.com
   python client.py
   ```

## Chạy client

```bash
python client.py
```

Client sẽ yêu cầu nhập `username` rồi sử dụng các lệnh:

- `1:1 @username : Nội dung`
- `1:N #channel : Nội dung` (chỉ Admin mới gửi được)
- `N:N #group : Nội dung`
- `subscribe #channel`
- `join #group`
- `list`
- `help`
- `voice @username : file.wav` (placeholder)
- `video #group : video_link` (placeholder)

## Mô tả chức năng

- Chat 1:1: gửi tin nhắn trực tiếp giữa hai người.
- Chat 1:N: chỉ Admin kênh mới gửi được, tin nhắn được chuyển tới thành viên kênh.
- Chat N:N: nhóm tất cả thành viên tham gia đều nhận và phản hồi.
- Voice/Video: hiện tại được hỗ trợ dưới dạng placeholder để mở rộng sau này với WebRTC hoặc truyền file/audio.

## Lưu ý

- Một người dùng không được trùng tên.
- Người dùng cần `subscribe` để nhận tin kênh và `join` để tham gia nhóm.
- Nếu muốn chạy server trên môi trường khác, đặt biến `PORT` trước khi khởi động server.
