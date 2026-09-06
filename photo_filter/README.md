# KATISTUDIO LỌC ẢNH

Ứng dụng Windows Desktop lọc và gom ảnh chuyên nghiệp dành cho studio ảnh cưới/tiệc/baby (**KATI STUDIO**).

## Tính năng chính
- Lọc ảnh thông minh theo danh sách mã, 4 số cuối tên file hoặc paste nguyên văn tin nhắn chọn ảnh từ khách hàng/bot Zalo/Discord/Web.
- Tự động gom toàn bộ ảnh đã chọn vào một thư mục duy nhất: `raw chọn`.
- Tự động tạo file báo cáo danh mục ảnh `danh_sach_chon_anh.txt` (phân nhóm: ẢNH BÀN, ẢNH LỚN, ALBUM...).
- Hỗ trợ đầy đủ định dạng ảnh và file RAW máy ảnh chuyên nghiệp (Canon `.cr2`, `.cr3`, Sony `.arw`, Nikon `.nef`, Fujifilm `.raf`, Adobe `.dng`...).
- Công cụ tìm ảnh bằng hình ảnh (AI Visual Match / Perceptual Hash) khi khách chỉ gửi ảnh chụp màn hình điện thoại.
- Giao diện Glassmorphism sang trọng với hình nền Studio KATI mờ sang trọng, tự động liên kết đến Fanpage Facebook KATI Studio khi nhấn vào thương hiệu.

## Khởi chạy từ mã nguồn
```powershell
cd d:\offline2\photo_filter
.\.venv\Scripts\Activate.ps1
python app.py
```

## Kiểm thử
```powershell
pytest
```

## Đóng gói ứng dụng Windows (Standalone .exe)
```powershell
pyinstaller photo_filter.spec
```
File thực thi độc lập sẽ được tạo tại: `d:\offline2\dist\KATISTUDIO.exe`.
