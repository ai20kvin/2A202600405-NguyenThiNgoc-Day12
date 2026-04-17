# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **API Key Hardcoded**: Lưu thông tin nhạy cảm (API Key, DB URL) ngay trong code dấn đến lộ lọt bí mật khi commit lên Git.
2. **Config Management**: Các tham số cấu hình (DEBUG, MAX_TOKENS) bị gán cứng, không linh hoạt khi chuyển đổi môi trường.
3. **Improper Logging**: Sử dụng lệnh `print()` cho mục đích debug, vừa chậm vừa khó phân tích log tập trung, dễ làm lộ secrets vào logs.
4. **Missing Health Checks**: Thiếu endpoint `/health` khiến các platform Cloud không biết khi nào ứng dụng crash để khởi động lại.
5. **Hardcoded Host/Port**: Gán cứng `localhost:8000` khiến ứng dụng không thể chạy trong Container hoặc Cloud (nơi Port được cấp phát động).

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | Hardcoded in `app.py` | Environment Variables (Pydantic/Config class) | Bảo mật, không lộ secrets, dễ thay đổi giữa các môi trường (Dev/Prod) mà không cần sửa code. |
| Health Check | Không có | Có `/health` và `/ready` endpoints | Giúp Cloud Platform tự động theo dõi trạng thái ứng dụng và tự restart khi cần. |
| Logging | Dùng lệnh `print()` | Structured JSON Logging | Dễ dàng thu thập và phân tích log tập trung (Datadog, Loki), tránh leak secrets. |
| Shutdown | Tắt đột ngột (Sudden) | Graceful Shutdown (Xử lý SIGTERM) | Đảm bảo hoàn thành các request đang dở dang trước khi tắt hẳn, tránh mất mát dữ liệu. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11` (Bản đầy đủ, nặng khoảng 1GB).
2. Working directory: `/app` (Thư mục làm việc chính bên trong container).
3. Tại sao COPY requirements.txt trước?: Để tận dụng **Docker Layer Cache**. Nếu file requirements không đổi, Docker sẽ bỏ qua bước cài đặt thư viện (vốn tốn thời gian nhất) giúp build nhanh hơn 10-20 lần.
4. CMD vs ENTRYPOINT: `CMD` cung cấp lệnh mặc định và có thể bị ghi đè khi chạy container qua command line. `ENTRYPOINT` mang tính cố định hơn, các tham số truyền vào khi chạy container sẽ được cộng dồn vào ENTRYPOINT.

### Exercise 2.3: Image size comparison
- Develop: ~1020 MB (Dùng image đầy đủ + lưu cả cache pip).
- Production: ~150 MB (Dùng image slim + Multi-stage build loại bỏ build-tools).
- Difference: ~85% (Giảm đáng kể dung lượng giúp push/pull ảnh nhanh hơn và bảo mật hơn).

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://2a202600405-nguyenthingoc-day12-production.up.railway.app
- Screenshot: [Link to screenshot in repo]

### Exercise 3.2: Comparison between railway.toml and render.yaml
- **Phạm vi (Scope)**: `railway.toml` tập trung vào cấu hình chạy của một service đơn lẻ. `render.yaml` (Blueprint) cho phép định nghĩa toàn bộ stack (Agent + Redis + DB) trong cùng một file.
- **Cơ chế Build**: Railway dùng Nixpacks tự động nhận diện ngôn ngữ. Render yêu cầu định nghĩa rõ `buildCommand`.
- **Quản lý Secrets**: Cả hai đều dùng Env vars, nhưng Render hỗ trợ `generateValue: true` để tự sinh secret key và `sync: false` để nhắc nhở set trên dashboard.
- **Định dạng**: TOML (Railway) vs YAML (Render).

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- **Auth (JWT)**: Login tại `/token` → Nhận JWT → Gửi kèm Header `Authorization: Bearer <token>`.
- **Rate Limit**: Sử dụng thuật toán **Sliding Window** với `deque`. 
    - User thường: 10 req/phút.
    - Admin: 100 req/phút. Khi vượt quá trả về lỗi **429 Too Many Requests**.

### Exercise 4.4: Cost guard implementation
- **Cách tiếp cận**: 
    - Theo dõi số lượng `input_tokens` và `output_tokens` cho mỗi request.
    - Tính toán chi phí dựa trên giá thực tế ($0.15/1M input tokens).
    - Lưu trữ lịch sử sử dụng trong ngày (trong thực tế dùng Redis).
    - Chặn request bằng mã lỗi **402 Payment Required** nếu user vượt mức $1/ngày hoặc hệ thống vượt mức $10/ngày.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- **Health Checks**: Đã triển khai `/health` (liveness) để kiểm tra trạng thái sống của process và `/ready` (readiness) để kiểm tra kết nối tới Redis trước khi cho phép nhận traffic.
- **Graceful Shutdown**: Sử dụng `lifespan` event trong FastAPI để xử lý tín hiệu SIGTERM, đảm bảo server không tắt đột ngột mà hoàn thành các request đang xử lý.
- **Stateless Design**: Refactor toàn bộ phần quản lý lịch sử trò chuyện sang Redis thay vì biến local. Mỗi request được đính kèm `session_id`, bất kỳ instance nào trong cụm cũng có thể truy xuất và tiếp tục cuộc hội thoại.
- **Load Balancing**: Sử dụng Nginx làm Load Balancer với Docker Compose (scale agent=3). Nginx phân phối traffic theo thuật toán Round Robin, giúp hệ thống chịu tải cao và đảm bảo tính sẵn sàng (High Availability).
- **Kiểm tra Stateless**: Khi chạy `test_stateless.py`, dù request gửi đến các instance khác nhau (id khác nhau), Agent vẫn nhớ được ngữ cảnh câu hỏi trước nhờ dữ liệu lưu tại Redis tập trung.
