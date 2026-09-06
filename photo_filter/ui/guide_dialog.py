from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class GuideDialog(QDialog):
    """Studio Dark User Guide Dialog with clear, visual step-by-step instructions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("KATISTUDIO - Hướng dẫn sử dụng")
        self.resize(680, 650)
        self.setMinimumSize(580, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("📖 Hướng dẫn sử dụng KATISTUDIO")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Quy trình chọn lọc ảnh studio chuyên nghiệp & nhanh chóng")
        subtitle.setStyleSheet("font-size: 12px; color: #9A8A8C;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        btn_close_top = QPushButton("✕ Đóng")
        btn_close_top.setProperty("class", "dialogAction")
        btn_close_top.clicked.connect(self.accept)
        header_layout.addWidget(btn_close_top)
        main_layout.addLayout(header_layout)

        # Scroll Area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 4, 10, 4)
        container_layout.setSpacing(12)

        # Step 1: Chọn thư mục
        container_layout.addWidget(
            self._create_guide_card(
                step="BƯỚC 1",
                badge_color="#D92534",
                title="Chọn thư mục nguồn & thư mục lưu",
                content=(
                    "• <b>Nơi chứa file gốc:</b> Bấm 'Chọn' để trỏ đến thư mục ảnh chụp từ máy ảnh "
                    "(hỗ trợ đọc cả thẻ nhớ SD/CFexpress hoặc ổ cứng).\n"
                    "• <b>Nơi lưu kết quả:</b> Chọn thư mục để lưu các ảnh đã được lọc.\n"
                    "• <i>Tích chọn 'Quét cả thư mục con'</i> nếu ảnh được phân loại trong nhiều folder nhỏ."
                ),
            )
        )

        # Step 2: Chọn định dạng
        container_layout.addWidget(
            self._create_guide_card(
                step="BƯỚC 2",
                badge_color="#FF9800",
                title="Chọn định dạng ảnh (.CR3, .CR2, .ARW, .NEF, .JPG...)",
                content=(
                    "• <b>Đuôi ảnh RAW máy ảnh:</b> Hỗ trợ đầy đủ các đuôi <code>.CR3</code>, <code>.CR2</code>, <code>.ARW</code>, <code>.NEF</code>, <code>.RAF</code>, <code>.DNG</code>...\n"
                    "• <b>Đuôi ảnh thông dụng:</b> <code>.JPG</code>, <code>.JPEG</code>, <code>.PNG</code>, <code>.HEIC</code>, <code>.TIFF</code>, <code>.WEBP</code>.\n"
                    "• <b>Đuôi file thiết kế:</b> <code>.PSD</code>, <code>.PSB</code>.\n"
                    "• Chọn <b>'Tất cả định dạng (*.*)'</b> để quét và lọc toàn bộ ảnh mà không cần quan tâm phần mở rộng."
                ),
            )
        )

        # Step 3: Chọn chế độ lọc (4 số cuối)
        container_layout.addWidget(
            self._create_guide_card(
                step="BƯỚC 3",
                badge_color="#20B59B",
                title="Chọn chế độ lọc ảnh (4 số cuối - Khuyên dùng cho Studio)",
                content=(
                    "Bấm vào hộp chọn bên phải chữ 'Danh sách tên file' để chọn kiểu lọc:\n"
                    "• 🌟 <b>4 số cuối (Khuyên dùng):</b> Khách hàng hoặc thợ chỉ cần gõ 4 số cuối của ảnh.\n"
                    "   <i>Ví dụ:</i> Nhập <code>1234</code> → Tự động lọc chính xác <code>IMG_1234.CR3</code>, <code>_MG_1234.JPG</code>, <code>DSC_1234.ARW</code>.\n"
                    "   <i>Ưu điểm:</i> Tránh nhầm lẫn với file 5 số (như <code>IMG_12345.JPG</code>).\n"
                    "• <b>Số cuối linh hoạt:</b> Nhập số bất kỳ (Ví dụ: <code>42</code> khớp <code>IMG_0042</code>, <code>DSC_0042</code>).\n"
                    "• <b>Có chứa ký tự:</b> Tìm bất kỳ ký tự nào nằm trong tên ảnh.\n"
                    "• <b>Tên chính xác:</b> So khớp 100% tên file (dành cho danh sách đầy đủ cả phần mở rộng)."
                ),
            )
        )

        # Step 4: Nhập danh sách mã & Dán tin nhắn Boss / Discord
        container_layout.addWidget(
            self._create_guide_card(
                step="BƯỚC 4",
                badge_color="#00BCD4",
                title="Nhập mã ảnh & Dán tin nhắn Boss / Discord / Web chọn ảnh",
                content=(
                    "• 🌟 <b>Dán trực tiếp tin nhắn từ Boss / Discord / Web chọn ảnh:</b> Bấm nút <code>📋 Dán tin Boss / Discord</code> hoặc dán toàn bộ tin nhắn thông báo (có chứa nhóm <code>ẢNH BÀN</code>, <code>ẢNH LỚN</code>, tên khách hàng...).\n"
                    "• 🌟 <b>Gom gọn gàng vào 1 thư mục 'raw chọn':</b> Ứng dụng mặc định gom toàn bộ file RAW vào một folder duy nhất là <code>raw chọn</code> để thuận tiện kéo vào Photoshop/Lightroom, đồng thời <b>tự động tạo file <code>danh_sach_chon_anh.txt</code> ghi chú chi tiết ảnh nào là ảnh bàn, ảnh lớn, album...</b>\n"
                    "• <b>Dán từ Excel, Word, Zalo:</b> Các mã cách nhau bằng <b>dấu cách (space), phẩy (,), tab hoặc xuống dòng</b> đều được nhận dạng chính xác.\n"
                    "• <i>Nút 'Điền tự động':</i> Bấm để nạp nhanh danh sách toàn bộ ảnh có trong thư mục nguồn."
                ),
            )
        )

        # Special Step: AI Visual Match (Khách chụp màn hình)
        container_layout.addWidget(
            self._create_guide_card(
                step="ĐẶC BIỆT",
                badge_color="#E67E22",
                title="🔍 Tìm ảnh từ ảnh chụp màn hình (AI Visual Match)",
                content=(
                    "• Dành cho trường hợp <b>khách hàng không ghi mã</b> mà chụp màn hình điện thoại gửi qua Zalo / Messenger.\n"
                    "• Bấm nút <b>'🔍 Tìm ảnh chụp (AI)'</b> ở góc trên bên phải màn hình chính.\n"
                    "• Chọn danh sách ảnh khách chụp màn hình và thư mục ảnh gốc máy ảnh (hỗ trợ cả ảnh RAW và JPG).\n"
                    "• Hệ thống AI tự động soi góc, băm ảnh perceptual hash để nhặt đúng file gốc vào mục <code>ẢNH CHỌN RAW</code>. Những ảnh mờ hoặc khó nhận diện sẽ đưa vào <code>ẢNH CHƯA TÌM THẤY</code> để kiểm tra lại."
                ),
            )
        )

        # Step 5: Thao tác & An toàn
        container_layout.addWidget(
            self._create_guide_card(
                step="BƯỚC 5",
                badge_color="#9C27B0",
                title="Thao tác & Kiểm tra kết quả an toàn",
                content=(
                    "• <b>Sao chép (Khuyên dùng):</b> Copy ảnh sang thư mục mới, giữ nguyên 100% ảnh gốc an toàn.\n"
                    "• <b>Di chuyển:</b> Chuyển hẳn ảnh sang thư mục đích (chỉ xóa nguồn khi đã ghi đích thành công).\n"
                    "• <b>Đổi tên theo mã:</b> Đổi tên file theo đúng mã đã nhập.\n"
                    "• <b>Xem trước & Báo cáo:</b> Bấm 'Tiến hành lọc' sẽ hiện bảng đối chiếu chi tiết trước khi bấm thực hiện. "
                    "Có thể bấm <b>'Xuất báo cáo (CSV/Excel)'</b> để lưu file kiểm kê."
                ),
            )
        )

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Bottom close button
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        btn_close = QPushButton("Đã hiểu • Đóng hướng dẫn")
        btn_close.setProperty("class", "dialogPrimary")
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)
        main_layout.addLayout(bottom_bar)

    def _create_guide_card(
        self, step: str, badge_color: str, title: str, content: str
    ) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background-color: #211819;"
            "  border: 1px solid #362627;"
            "  border-radius: 10px;"
            "  padding: 10px;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        lbl_step = QLabel(f" {step} ")
        lbl_step.setStyleSheet(
            f"background-color: {badge_color}; color: #FFFFFF; font-size: 10px; "
            f"font-weight: 800; border-radius: 4px; padding: 2px 6px;"
        )
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        header_row.addWidget(lbl_step)
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        lbl_content = QLabel(content)
        lbl_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_content.setWordWrap(True)
        lbl_content.setStyleSheet(
            "font-size: 12px; color: #C5B6B8; line-height: 140%;"
        )
        layout.addWidget(lbl_content)

        return card


__all__ = ["GuideDialog"]
