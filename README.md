# KATISTUDIO LỌC ẢNH (BÀN GIAO DỰ ÁN CHO DEVELOPER)

> **Dự án**: Phần mềm Windows Desktop chuyên dụng lọc và gom file ảnh (RAW + JPG) cho Studio ảnh nghệ thuật / tiệc cưới / baby (**KATI STUDIO**).  
> **Trạng thái hiện tại**: **Giai đoạn 1 Hoàn thiện (Production Ready - 100%)**. Ứng dụng đang hoạt động ổn định, đã đóng gói thành file thực thi độc lập `dist/KATISTUDIO.exe`, vượt qua toàn bộ 18/18 test case tự động.

---

## 1. Bối cảnh & Bài toán nghiệp vụ (Studio Workflow)

Trong quy trình làm việc thực tế tại KATI STUDIO:
1. **Dữ liệu nguồn**: Thợ chụp trả về thẻ nhớ hoặc thư mục chứa hàng trăm đến hàng nghìn file ảnh RAW máy ảnh (Canon `.cr2`, `.cr3`, Sony `.arw`, Nikon `.nef`, Fuji `.raf`...) kèm file JPG.
2. **Khách hàng chọn ảnh**: Khách hàng hoặc Boss gửi danh sách ảnh qua Zalo, Discord, Messenger hoặc web theo cú pháp tin nhắn có phân loại nhóm (ví dụ: `ẢNH BÀN`, `ẢNH LỚN`, `ẢNH CỔNG`, `ALBUM`, `ẢNH TẶNG`...) hoặc gửi danh sách số hiệu / 4 số cuối của file.
3. **Yêu cầu xử lý của phần mềm**:
   - **Tập trung vào 1 thư mục duy nhất**: Toàn bộ ảnh khách đã chọn phải được copy/move vào đúng một thư mục tên là **`raw chọn`** nằm trong thư mục đích (ví dụ: `D:\2026\04.09 baby\raw chọn\`) để thợ Photoshop/Lightroom kéo cả thư mục vào chỉnh sửa hàng loạt mà không bị phân tán vào các thư mục con.
   - **Không nhân bản (Tránh trùng file)**: Nếu 1 bức ảnh vừa thuộc nhóm `ẢNH BÀN` vừa thuộc nhóm `ẢNH LỚN`, phần mềm chỉ lưu **duy nhất 1 file** vào `raw chọn` để tiết kiệm dung lượng ổ cứng.
   - **Xuất file báo cáo chi tiết**: Tự động sinh file **`danh_sach_chon_anh.txt`** đặt cùng cấp với `raw chọn`, liệt kê rõ ràng từng nhóm mục (ẢNH BÀN: gồm những ảnh nào, ẢNH LỚN: gồm những ảnh nào...) kèm bảng đối chiếu chi tiết từng file.
   - **Tìm ảnh bằng hình ảnh (AI Visual Match)**: Trường hợp khách hàng chụp màn hình điện thoại gửi qua Zalo (không ghi mã số), phần mềm có công cụ đối chiếu bằng thuật toán Perceptual Hash (`imagehash`) để tìm ra file gốc tương ứng trong thư mục ảnh.

---

## 2. Tech Stack & Môi trường yêu cầu

- **Hệ điều hành**: Windows 10 / 11 (64-bit).
- **Ngôn ngữ**: Python 3.10+ (Đã test và đóng gói chuẩn trên Python 3.10.6 & 3.12).
- **UI Framework**: `PySide6` (Qt for Python 6.11+).
- **Xử lý ảnh & Hash**: `Pillow`, `rawpy`, `imagehash`, `numpy`, `scipy`.
- **Đóng gói**: `PyInstaller` (Onefile GUI executable, không hiện console đen).
- **Kiểm thử**: `pytest`, `pytest-qt`.

---

## 3. Cấu trúc thư mục dự án

```text
d:\offline2\
├── dist/
│   └── KATISTUDIO.exe             # Bản build độc lập đã hoàn thiện, sẵn sàng sử dụng
├── photo_filter/                  # Mã nguồn chính của dự án
│   ├── models/
│   │   └── transfer_item.py       # Dataclass TransferItem đại diện cho 1 file ảnh, mã khớp, đích đến, trạng thái
│   ├── services/
│   │   ├── scanner.py             # Quét đệ quy thư mục ảnh, lọc extension RAW/JPG, bảo vệ đường dẫn
│   │   ├── matcher.py             # Logic đối chiếu mã: chính xác, chứa, bắt đầu, kết thúc, 4 số cuối
│   │   ├── message_parser.py      # Bộ phân tích cú pháp tin nhắn Zalo/Discord/Web từ khách/boss
│   │   ├── organizer.py           # Quản lý sao chép/di chuyển file vào thư mục "raw chọn", chống trùng lặp
│   │   ├── report.py              # Xuất file danh_sach_chon_anh.txt, CSV, JSON
│   │   ├── visual_matcher.py      # Thuật toán so khớp ảnh qua pHash đối chiếu ảnh chụp màn hình
│   │   ├── security.py            # Module bảo mật: Anti-debug, Anti-tamper, phát hiện công cụ crack & watchdog ngầm
│   │   └── worker.py              # QThread Worker chạy nền, không gây đơ giao diện khi xử lý nhiều file
│   ├── ui/
│   │   ├── main_window.py         # Cửa sổ chính: bố cục Glassmorphism, header KATI STUDIO, form nhập liệu
│   │   ├── results_dialog.py      # Bảng kết quả lọc, thống kê file tìm thấy, file thiếu
│   │   ├── visual_match_dialog.py # Dialog chức năng tìm ảnh bằng hình ảnh AI
│   │   ├── guide_dialog.py        # Hộp thoại hướng dẫn sử dụng chi tiết từng bước
│   │   ├── styles.qss             # Bảng mã CSS/QSS giao diện tối sang trọng (Studio Luxury Glass)
│   │   └── assets/                # Tài nguyên: logo.ico, app_logo.png, studio_bg.jpg, các icon SVG
│   ├── tests/                     # Bộ 19 unit tests tự động
│   │   ├── test_boss_message.py   # Test bóc tách tin nhắn phân loại nhóm
│   │   ├── test_matcher.py        # Test các chế độ khớp mã và 4 số cuối
│   │   ├── test_organizer.py      # Test copy/move và tạo thư mục "raw chọn"
│   │   ├── test_report.py         # Test xuất báo cáo txt, csv, json
│   │   ├── test_scanner.py        # Test quét ảnh và trường hợp thư mục đích là cha của nguồn
│   │   ├── test_security.py       # Test module bảo mật và môi trường runtime
│   │   └── test_visual_matcher.py # Test so khớp perceptual hash
│   ├── app.py                     # Entry point khởi tạo QApplication và kích hoạt bảo mật
│   ├── build_nuitka.bat           # File batch biên dịch Native C/C++ chống dịch ngược với 1 cú click
│   ├── photo_filter.spec          # File cấu hình PyInstaller đóng gói onefile
│   └── requirements.txt           # Danh sách thư viện cần thiết
├── .gitignore                     # Cấu hình bỏ qua file rác, cache, thư mục venv
└── README.md                      # Tài liệu bàn giao này
```

---

## 4. Các tính năng & Module cốt lõi đã hoàn thành

### 4.1. Quét file thông minh & Khắc phục lỗi loại trừ đường dẫn (`services/scanner.py`)
- **Hỗ trợ định dạng toàn diện**:
  - Ảnh thông thường: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.tif`, `.psd`...
  - Tất cả định dạng RAW chuyên nghiệp: Canon (`.cr2`, `.cr3`, `.crw`), Sony (`.arw`, `.srf`, `.sr2`), Nikon (`.nef`, `.nrw`), Fujifilm (`.raf`), Lumix (`.rw2`), Olympus (`.orf`), Universal/Adobe/Leica (`.dng`, `.rwl`), Pentax (`.pef`), Hasselblad (`.3fr`, `.fff`), Phase One (`.iiq`), Sigma (`.x3f`)...
  - Tự động bỏ qua file hệ thống rác: `desktop.ini`, `thumbs.db`, `.ds_store`.
- **Xử lý triệt để bug Ancestor Directory**:
  - Trước đây, khi người dùng chọn thư mục nguồn là thẻ nhớ con (ví dụ: `.../job/100MSDCF`) và đích là thư mục cha (`.../job`), bộ quét nhầm lẫn đích nằm trong phạm vi cần loại trừ khiến kết quả trả về 0 file.
  - Hiện tại, hàm `scan_images` kiểm tra chính xác `candidate_exclude != source_dir and _is_within(candidate_exclude, source_dir)`, chỉ loại trừ nếu thư mục đích thực sự là một thư mục con nằm sâu bên trong nguồn.

### 4.2. Khớp mã linh hoạt & Bóc tách tin nhắn Boss (`services/matcher.py`, `services/message_parser.py`)
- Hỗ trợ 5 chế độ so khớp:
  1. `MODE_LAST_4_DIGITS` (4 số cuối - **Mặc định & Khuyên dùng cho máy ảnh**): Khớp 4 chữ số cuối của tên file mà không phụ thuộc vào tiền tố camera (ví dụ nhập `0212` sẽ khớp trúng `_DSC0212.ARW`, `A7500212.JPG`, `IMG_0212.CR3`).
  2. `MODE_EXACT`: Khớp chính xác tên file (có hoặc không có phần mở rộng).
  3. `MODE_CONTAINS`: Tên file có chứa chuỗi mã.
  4. `MODE_STARTS_WITH`: Bắt đầu bằng mã.
  5. `MODE_ENDS_WITH`: Kết thúc bằng mã.
- **Tự động bóc tách tin nhắn chat**:
  - Nhận diện các tiêu đề: Khách hàng, Thư mục/Thẻ nhớ, Ngày chụp.
  - Nhận diện các nhóm phân loại: `ẢNH BÀN`, `ẢNH LỚN`, `ẢNH CỔNG`, `ALBUM`, `ẢNH TẶNG`, v.v.
  - Bóc tách toàn bộ mã ảnh từ tin nhắn vào danh sách xử lý và giữ nguyên phân loại để ghi vào báo cáo `danh_sach_chon_anh.txt`.

### 4.3. Gom ảnh vào thư mục `raw chọn` & Báo cáo (`services/organizer.py`, `services/report.py`)
- Khi thực thi (Sao chép hoặc Di chuyển):
  - Tự động tạo thư mục: `<Thư_mục_đích>/[Tên_khách_hàng/]raw chọn/`.
  - Toàn bộ file được gom về đây. Nếu một file thỏa mãn nhiều danh mục, hệ thống tự deduplicate, chỉ copy đúng 1 lần duy nhất.
  - Tạo file `danh_sach_chon_anh.txt` với định dạng phân nhóm rõ ràng, chi tiết từng file khớp với nhóm nào.

### 4.4. Giao diện người dùng (`ui/main_window.py`, `ui/styles.qss`)
- **Thiết kế Studio Luxury Glassmorphism**: Sử dụng hình nền Studio của KATI phủ lớp nền đen mờ sang trọng, các ô nhập liệu, dropdown và bảng đều có độ trong suốt tinh tế.
- **Tiêu đề cửa sổ (Title Bar)**: `KATISTUDIO LỌC ẢNH`.
- **Header thương hiệu KATI STUDIO**:
  - Logo máy ảnh sắc nét.
  - Tên thương hiệu: **`KATI STUDIO`** (khoảng cách chữ cân đối, không bị tràn viền hay mất chữ).
  - Dòng phụ: **`LỌC ẢNH CHUYÊN NGHIỆP`**.
  - **Tương tác click**: Khi người dùng nhấn vào logo hoặc chữ `KATI STUDIO`, phần mềm tự động bật trình duyệt web truy cập trang Facebook chính thức của studio: `https://www.facebook.com/katiphotographer/`.
- **Nút công cụ nhanh trên Header**:
  - `🔍 Tìm ảnh AI`: Mở dialog tìm ảnh bằng hình ảnh qua pHash.
  - `📖 Hướng dẫn`: Mở bảng hướng dẫn sử dụng chi tiết từng bước.
- **Lưu trạng thái cấu hình**: Tự động ghi nhớ thư mục nguồn, đích, định dạng và thao tác vào Windows Registry (`HKCU:\Software\KATISTUDIO\KATISTUDIO Filter`) để người dùng không phải chọn lại sau mỗi lần mở app.

### 4.5. Bảo mật chống dịch ngược & Anti-Crack nhiều lớp (`services/security.py` + Nuitka)
1. **Biên dịch mã máy Native C/C++ (Nuitka + MSVC 2022)**:
   - Thay vì đóng gói bytecode `.pyc` dễ dàng bị unpack bởi các công cụ như `pyinstxtractor` hay `uncompyle6`, dự án sử dụng **Nuitka** để biên dịch toàn bộ code Python trực tiếp sang mã C/C++ và link thành file nhị phân x86_64 native machine code.
   - Triệt tiêu hoàn toàn chữ ký PyInstaller (`MEI\014\013...`) và không lưu trữ bytecode Python có thể dịch ngược.
2. **Cơ chế chống Debugger (Anti-Debugging)**:
   - Tích hợp kiểm tra trực tiếp Win32 API: `IsDebuggerPresent()`, `CheckRemoteDebuggerPresent()`, và `NtQueryInformationProcess(ProcessDebugPort)`.
   - Kiểm tra trực tiếp cờ `BeingDebugged` trong khối môi trường tiến trình (PEB).
3. **Phát hiện công cụ dịch ngược và can thiệp bộ nhớ (Tool Blacklist)**:
   - Sử dụng `CreateToolhelp32Snapshot` của Windows kernel quét nhanh danh sách tiến trình đang chạy.
   - Tự động chặn và thoát ngay nếu phát hiện các công cụ crack/debug: `x64dbg`, `x32dbg`, `IDA Pro`, `Ghidra`, `Cheat Engine`, `Process Hacker`, `Process Explorer`, `dnSpy`, `Scylla`, `HTTP Debugger`, `Wireshark`...
4. **Luồng giám sát ngầm (Security Watchdog Daemon)**:
   - Khởi chạy một thread nền chạy định kỳ mỗi 3 giây (`KatiSecWatchdog`) để phát hiện hành vi gắn debugger động (Attach Debugger) hoặc mở công cụ can thiệp trong lúc phần mềm đang chạy. Nếu vi phạm, tiến trình tự ngắt ngay lập tức bằng `os._exit(0)` để chống memory dumping.

---

## 5. Hướng dẫn cài đặt môi trường cho Developer mới

### Bước 1: Chuẩn bị môi trường Python
Mở PowerShell tại thư mục dự án:
```powershell
cd d:\offline2\photo_filter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Bước 2: Chạy ứng dụng từ mã nguồn (Development Mode)
```powershell
python app.py
```

### Bước 3: Chạy toàn bộ Unit Tests
```powershell
pytest
```
*Tất cả 19 test cases phải đạt màu xanh (19 passed).*

### Bước 4: Biên dịch ứng dụng sang Native C/C++ chống dịch ngược (Khuyên dùng)
Chạy file batch có sẵn hoặc lệnh Nuitka:
```powershell
cd d:\offline2\photo_filter
.\build_nuitka.bat
```
Hoặc chạy lệnh PowerShell:
```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --enable-plugin=pyside6 `
  --windows-disable-console `
  --windows-icon-from-ico="photo_filter/ui/assets/app_logo.ico" `
  --windows-company-name="KATISTUDIO" `
  --windows-product-name="KATISTUDIO LỌC ẢNH" `
  --windows-file-version=1.0.0.0 `
  --windows-product-version=1.0.0.0 `
  --windows-file-description="KATISTUDIO LỌC ẢNH" `
  --include-package=photo_filter `
  --include-data-dir="photo_filter/ui=photo_filter/ui" `
  --include-data-dir="photo_filter/ui=ui" `
  --output-dir="..\dist" `
  --output-filename=KATISTUDIO.exe `
  --assume-yes-for-downloads `
  app.py
```
File thực thi bảo vệ cuối cùng sẽ xuất hiện tại `d:\offline2\dist\KATISTUDIO.exe`.

*(Tùy chọn phụ)* Nếu muốn đóng gói nhanh bằng PyInstaller để test nhanh:
```powershell
pyinstaller --clean photo_filter.spec
```

---

## 6. Các điểm lưu ý kỹ thuật (Gotchas & Important Notes)

1. **Cơ chế nạp Asset trong `resolve_asset()`** (`ui/main_window.py`):
   - Khi chạy từ mã nguồn: Đường dẫn trỏ tới `photo_filter/ui/assets/`.
   - Khi chạy qua file đóng gói PyInstaller: Đường dẫn nằm trong thư mục tạm `sys._MEIPASS`. Hàm `resolve_asset()` đã được viết để tự động tìm kiếm linh hoạt ở cả 2 môi trường. Nếu thêm icon hay hình ảnh mới, cần đặt vào `photo_filter/ui/assets/` và cập nhật danh sách `datas` trong file `photo_filter.spec`.
2. **Không chặn giao diện chính (UI Thread Blocking)**:
   - Các thao tác quét thư mục nhiều file, sao chép dung lượng lớn (hàng chục GB file RAW) và tính toán hash ảnh bắt buộc phải giao cho `FilterWorker` (`QThread`) xử lý và phát tín hiệu `progress`, `finished` về giao diện chính. Tuyệt đối không gọi trực tiếp các vòng lặp I/O lớn trên `MainWindow`.
3. **Quy tắc bảo vệ dữ liệu khách hàng**:
   - Mặc định thao tác là **Sao chép (Copy)** để bảo toàn 100% file gốc trên thẻ nhớ máy ảnh của khách hàng. Thao tác Di chuyển (Move) chỉ được thực hiện khi người dùng chủ động tích chọn.

---

## 7. Đề xuất Roadmap / Hướng phát triển tiếp theo (Cho Dev tiếp nhận)

Nếu studio có nhu cầu nâng cấp thêm trong các phiên bản sau, developer có thể tiếp tục phát triển các hướng sau:
1. **Xem trước ảnh Thumbnail (Preview Thumbnail)**:
   - Trong bảng `ResultsDialog`, bổ sung một cột ảnh thu nhỏ hoặc panel preview khi nhấp vào từng dòng file (sử dụng thư viện `rawpy` trích xuất embedded JPEG preview của file RAW rất nhanh mà không tốn tài nguyên).
2. **Kéo thả thư mục (Drag & Drop)**:
   - Cho phép người dùng kéo thả trực tiếp thư mục từ Windows Explorer vào ô "Thư mục ảnh gốc" hoặc "Thư mục lưu kết quả".
3. **Tự động đóng gói ZIP**:
   - Bổ sung tùy chọn nén tự động thư mục `raw chọn` thành file `.zip` sau khi lọc để tiện gửi qua Google Drive / OneDrive cho thợ photoshop ở xa.
4. **Hỗ trợ xuất sang Lightroom Catalog / XML / XMP**:
   - Xuất file `.xmp` đánh dấu sao (Rating 5 sao) hoặc nhãn màu (Color label) trực tiếp vào file RAW để khi mở trong Lightroom/Bridge, các ảnh được chọn sẽ tự động được gắn cờ.

---
*Tài liệu được tổng hợp và chuẩn hóa đầy đủ bởi KATI STUDIO Technical Team.*
