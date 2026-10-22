# Hệ thống Quản lý Hợp đồng

## 1. Giới thiệu

Hệ thống Quản lý Hợp đồng được xây dựng nhằm hỗ trợ lưu trữ, quản lý và tra cứu thông tin hợp đồng trên một nền tảng tập trung. Dự án sử dụng Django cho phần ứng dụng web và PostgreSQL để quản lý dữ liệu.

## 2. Công nghệ sử dụng

- **Ngôn ngữ:** Python
- **Framework:** Django 5.2
- **Cơ sở dữ liệu:** PostgreSQL 17
- **Môi trường chạy cơ sở dữ liệu:** Docker Compose
- **Công cụ quản trị cơ sở dữ liệu:** pgAdmin

## 3. Cấu trúc dự án

- `manage.py`: Điểm vào quản lý ứng dụng Django.
- `config/`: Cấu hình dự án.
- `contracts/`: Ứng dụng quản lý hợp đồng.
- `docker-compose.yml`: Cấu hình dịch vụ PostgreSQL và pgAdmin.

## 4. Yêu cầu môi trường

- Python và môi trường ảo Python.
- Docker Engine và Docker Compose.
- Các thư viện được khai báo trong file phụ thuộc của dự án.

## 5. Cấu hình và chạy dự án

1. Tạo file `.env` từ mẫu cấu hình nếu dự án có cung cấp.
2. Khai báo các biến môi trường cần thiết, bao gồm thông tin kết nối cơ sở dữ liệu và `DJANGO_SECRET_KEY`.
3. Khởi động cơ sở dữ liệu:

   ```bash
   docker compose up -d
   ```

4. Kích hoạt môi trường ảo:

   ```bash
   source .venv/bin/activate
   ```

5. Cài đặt các thư viện theo file phụ thuộc của dự án.
6. Kiểm tra cấu hình:

   ```bash
   python manage.py check
   ```

7. Khởi chạy ứng dụng:

   ```bash
   python manage.py runserver
   ```

8. Mở trình duyệt tại `http://127.0.0.1:8000/`.

## 6. Quản trị cơ sở dữ liệu

Nếu pgAdmin đang chạy theo cấu hình Docker Compose, có thể truy cập tại `http://127.0.0.1:5050/`.

## 7. Bảo mật

- Không đưa file `.env`, mật khẩu, khóa bí mật hoặc dữ liệu cá nhân lên GitHub.
- Sử dụng biến môi trường để lưu thông tin nhạy cảm.
- Không sử dụng chế độ debug khi triển khai thực tế.

## 8. Trạng thái kiểm tra

- Django system check: đạt tại thời điểm kiểm tra.
- Kết nối Django với PostgreSQL: thành công tại thời điểm kiểm tra.

## 9. Định hướng phát triển

Tiếp tục hoàn thiện các chức năng quản lý hợp đồng, kiểm thử và bổ sung tài liệu hướng dẫn sử dụng.

