from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Event

from PySide6.QtCore import QSettings, QSize, QThread, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QIcon,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_filter.models.transfer_item import TransferItem, TransferStatus
from photo_filter.services.matcher import (
    MODE_CONTAINS,
    MODE_ENDS_WITH,
    MODE_EXACT,
    MODE_LAST_4_DIGITS,
    MODE_STARTS_WITH,
    MODE_TRAILING_DIGITS,
    normalize_codes,
)
from photo_filter.services.message_parser import (
    ParsedSelectionMessage,
    parse_selection_message,
)
from photo_filter.services.report import export_report
from photo_filter.services.scanner import scan_images
from photo_filter.services.worker import FilterWorker
from photo_filter.ui.guide_dialog import GuideDialog
from photo_filter.ui.results_dialog import ResultsDialog
from photo_filter.ui.visual_match_dialog import VisualMatchDialog


def resolve_asset(filename: str) -> Path:
    """Robustly resolve asset path in dev environment, PyInstaller bundle, or fallback."""
    # 1. PyInstaller frozen path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        for cand in [
            meipass / "ui" / "assets" / filename,
            meipass / "photo_filter" / "ui" / "assets" / filename,
            meipass / "assets" / filename,
            meipass / filename,
        ]:
            if cand.exists():
                return cand

    # 2. Local module path & cwd
    module_dir = Path(__file__).resolve().parent
    for cand in [
        module_dir / "assets" / filename,
        module_dir.parent / "ui" / "assets" / filename,
        module_dir.parent.parent / "photo_filter" / "ui" / "assets" / filename,
        Path.cwd() / "photo_filter" / "ui" / "assets" / filename,
        Path.cwd() / "ui" / "assets" / filename,
    ]:
        if cand.exists():
            return cand

    # 3. Dedicated user desktop fallback for background image
    if filename == "studio_bg.jpg":
        desktop_img = Path(r"C:\Users\KATI STUDIO\Desktop\708228410_2198117567694961_1539079236499629896_n.jpg")
        if desktop_img.exists():
            return desktop_img

    return module_dir / "assets" / filename


class StudioBackgroundWidget(QWidget):
    """Luxury Studio dark background widget rendering the customized KATI STUDIO backdrop with an elegant dark overlay."""

    def __init__(self, bg_image_path: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("centralWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        # Resolve pixmap from provided path, resolve_asset, or desktop fallback
        target_path = bg_image_path
        if not target_path or not Path(target_path).exists():
            target_path = resolve_asset("studio_bg.jpg")

        self.bg_image_path = target_path
        self._pixmap: QPixmap | None = None

        if target_path and Path(target_path).exists():
            pix = QPixmap(str(target_path))
            if not pix.isNull():
                self._pixmap = pix

        if self._pixmap is None or self._pixmap.isNull():
            desktop_img = Path(r"C:\Users\KATI STUDIO\Desktop\708228410_2198117567694961_1539079236499629896_n.jpg")
            if desktop_img.exists():
                pix = QPixmap(str(desktop_img))
                if not pix.isNull():
                    self._pixmap = pix

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Base obsidian studio background
        painter.fillRect(self.rect(), QColor("#140E0F"))

        if self._pixmap and not self._pixmap.isNull():
            # Scale background to fill while maintaining aspect ratio
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center alignment
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

            # Phủ 1 lớp đen mờ sang trọng làm nổi bật ảnh chân dung studio và hỗ trợ giao diện trong suốt
            painter.fillRect(self.rect(), QColor(0, 0, 0, 95))

        super().paintEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("KATISTUDIO", "KATISTUDIO Filter")
        self.preview_items: list[TransferItem] = []
        self.last_items: list[TransferItem] = []
        self.worker: FilterWorker | None = None
        self.thread: QThread | None = None
        self.cancel_event: Event | None = None
        self.parsed_message: ParsedSelectionMessage | None = None

        self.assets_dir = resolve_asset("studio_bg.jpg").parent
        self._build_ui()
        self._restore_settings()

    def _get_icon(self, filename: str) -> QIcon:
        path = resolve_asset(filename)
        return QIcon(str(path)) if path.exists() else QIcon()

    def _build_ui(self) -> None:
        self.setWindowTitle("KATISTUDIO LỌC ẢNH")
        self.setMinimumSize(560, 840)
        self.resize(580, 880)

        # Set Window Icon
        logo_ico = resolve_asset("app_logo.ico")
        if not logo_ico.exists():
            logo_ico = resolve_asset("logo.ico")
        if logo_ico.exists():
            self.setWindowIcon(QIcon(str(logo_ico)))
        else:
            logo_png = resolve_asset("app_logo.png")
            if logo_png.exists():
                self.setWindowIcon(QIcon(str(logo_png)))

        logo_png = resolve_asset("app_logo.png")
        bg_path = resolve_asset("studio_bg.jpg")
        central = StudioBackgroundWidget(bg_path, self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 20, 32, 18)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # Header: Brand & Title & Quick Guide Button & AI Visual Match
        # -------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        # App Logo Icon
        if logo_png.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_png)).scaled(
                42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
            logo_label.setToolTip("Nhấn để mở Facebook: KATI Studio (facebook.com/katiphotographer)")
            logo_label.mousePressEvent = lambda _event: self._open_facebook_page()
            header_row.addWidget(logo_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_label = QLabel("KATI STUDIO")
        title_label.setObjectName("brandTitle")
        title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        title_label.setToolTip("Nhấn để mở Facebook: KATI Studio (facebook.com/katiphotographer)")
        title_label.mousePressEvent = lambda _event: self._open_facebook_page()

        subtitle_label = QLabel("LỌC ẢNH CHUYÊN NGHIỆP")
        subtitle_label.setObjectName("brandSubtitle")
        subtitle_label.setCursor(Qt.CursorShape.PointingHandCursor)
        subtitle_label.setToolTip("Nhấn để mở Facebook: KATI Studio (facebook.com/katiphotographer)")
        subtitle_label.mousePressEvent = lambda _event: self._open_facebook_page()

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header_row.addLayout(title_box)

        header_row.addStretch()

        # AI Visual Match Button (From GOM ẢNH RAW KATI STUDIO)
        self.btn_ai_visual = QPushButton("  🔍 Tìm ảnh AI")
        self.btn_ai_visual.setObjectName("aiVisualButton")
        self.btn_ai_visual.setToolTip(
            "Dành cho trường hợp khách gửi ảnh chụp màn hình điện thoại (Zalo/Facebook) thay vì gõ mã"
        )
        self.btn_ai_visual.clicked.connect(self._open_ai_visual_match)
        header_row.addWidget(self.btn_ai_visual)

        # "Hướng dẫn sử dụng" pill button in Header
        self.btn_guide_top = QPushButton("  📖 Hướng dẫn")
        self.btn_guide_top.setProperty("class", "pillButton")
        self.btn_guide_top.setIcon(self._get_icon("info.svg"))
        self.btn_guide_top.setIconSize(QSize(14, 14))
        self.btn_guide_top.setToolTip("Mở bảng hướng dẫn sử dụng chi tiết từng bước")
        self.btn_guide_top.clicked.connect(self._open_guide)
        header_row.addWidget(self.btn_guide_top)

        layout.addLayout(header_row)
        layout.addSpacing(4)

        # -------------------------------------------------------------
        # Section 1: Thư mục nguồn
        # -------------------------------------------------------------
        lbl_source = QLabel("Nơi chứa các file gốc cần lọc")
        lbl_source.setProperty("class", "form-label")
        layout.addWidget(lbl_source)

        row_source = QHBoxLayout()
        row_source.setSpacing(10)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Chưa chọn thư mục")
        self.source_input.setReadOnly(True)

        self.btn_source = QPushButton("  Chọn")
        self.btn_source.setObjectName("browseButton")
        self.btn_source.setIcon(self._get_icon("folder.svg"))
        self.btn_source.setIconSize(QSize(18, 18))
        self.btn_source.clicked.connect(lambda: self._select_directory(self.source_input))

        row_source.addWidget(self.source_input, 1)
        row_source.addWidget(self.btn_source)
        layout.addLayout(row_source)
        layout.addSpacing(2)

        # -------------------------------------------------------------
        # Section 2: Thư mục đích
        # -------------------------------------------------------------
        lbl_dest = QLabel("Nơi lưu các file sau khi lọc")
        lbl_dest.setProperty("class", "form-label")
        layout.addWidget(lbl_dest)

        row_dest = QHBoxLayout()
        row_dest.setSpacing(10)
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Chưa chọn thư mục")
        self.dest_input.setReadOnly(True)

        self.btn_dest = QPushButton("  Chọn")
        self.btn_dest.setObjectName("browseButton")
        self.btn_dest.setIcon(self._get_icon("folder.svg"))
        self.btn_dest.setIconSize(QSize(18, 18))
        self.btn_dest.clicked.connect(lambda: self._select_directory(self.dest_input))

        row_dest.addWidget(self.dest_input, 1)
        row_dest.addWidget(self.btn_dest)
        layout.addLayout(row_dest)
        layout.addSpacing(4)

        # -------------------------------------------------------------
        # Section 3: Định dạng file (Signature Red Border Combobox)
        # -------------------------------------------------------------
        row_format = QHBoxLayout()
        lbl_format = QLabel("Định dạng file")
        lbl_format.setProperty("class", "form-label")
        row_format.addWidget(lbl_format)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("formatCombo")
        format_options = [
            ("Tất cả định dạng (*.*)", None),
            (".JPG, .JPEG", (".jpg", ".jpeg")),
            (".CR3, .CR2, .CRW", (".cr3", ".cr2", ".crw")),
            (".ARW, .SRF, .SR2", (".arw", ".srf", ".sr2")),
            (".NEF, .NRW", (".nef", ".nrw")),
            (".RAF", (".raf",)),
            (".DNG", (".dng", ".rwl")),
            ("Tất cả đuôi RAW (.CR3, .CR2, .ARW, .NEF, .RAF, .DNG...)", (
                ".cr3", ".cr2", ".crw", ".arw", ".srf", ".sr2",
                ".nef", ".nrw", ".raf", ".rw2", ".orf", ".dng",
                ".pef", ".ptx", ".3fr", ".iiq", ".x3f"
            )),
            (".PNG", ".png"),
            (".HEIC, .HEIF, .AVIF", (".heic", ".heif", ".avif")),
            (".TIFF, .TIF", (".tif", ".tiff")),
            (".PSD, .PSB", (".psd", ".psb")),
            (".WEBP", ".webp"),
        ]
        for label, val in format_options:
            self.format_combo.addItem(label, val)

        row_format.addWidget(self.format_combo, 1)
        layout.addLayout(row_format)
        layout.addSpacing(4)

        # -------------------------------------------------------------
        # Section 4: Danh sách tên file & Tùy chọn lọc
        # -------------------------------------------------------------
        row_list_header = QHBoxLayout()
        row_list_header.setSpacing(8)

        lbl_list = QLabel("Danh sách tên file")
        lbl_list.setProperty("class", "form-label")
        row_list_header.addWidget(lbl_list)
        row_list_header.addStretch()

        # Mode combobox ("4 số cuối (Khuyên dùng)", etc.)
        self.match_mode_combo = QComboBox()
        self.match_mode_combo.setProperty("class", "pillCombo")
        self.match_mode_combo.addItem("4 số cuối (1234 -> IMG_1234)", MODE_LAST_4_DIGITS)
        self.match_mode_combo.addItem("Số cuối linh hoạt (42 -> IMG_0042)", MODE_TRAILING_DIGITS)
        self.match_mode_combo.addItem("Có chứa ký tự", MODE_CONTAINS)
        self.match_mode_combo.addItem("Tên file chính xác", MODE_EXACT)
        self.match_mode_combo.addItem("Bắt đầu bằng mã", MODE_STARTS_WITH)
        self.match_mode_combo.addItem("Kết thúc bằng mã", MODE_ENDS_WITH)
        self.match_mode_combo.setIconSize(QSize(14, 14))
        self.match_mode_combo.currentIndexChanged.connect(self._on_match_mode_changed)
        row_list_header.addWidget(self.match_mode_combo)

        # "Dán tin nhắn Boss / Discord" pill button
        self.btn_paste_boss = QPushButton(" 📋 Dán tin Boss / Discord")
        self.btn_paste_boss.setProperty("class", "pillButton")
        self.btn_paste_boss.setIconSize(QSize(14, 14))
        self.btn_paste_boss.setToolTip("Dán nhanh tin nhắn chọn ảnh từ Zalo / Messenger / Discord / Web vào ứng dụng")
        self.btn_paste_boss.clicked.connect(self._paste_from_clipboard)
        row_list_header.addWidget(self.btn_paste_boss)

        # "Điền tự động" pill button
        self.btn_autofill = QPushButton("  Điền tự động")
        self.btn_autofill.setProperty("class", "pillButton")
        self.btn_autofill.setIcon(self._get_icon("info.svg"))
        self.btn_autofill.setIconSize(QSize(14, 14))
        self.btn_autofill.setToolTip("Tự động đọc danh sách tên file có trong thư mục nguồn")
        self.btn_autofill.clicked.connect(self._autofill_codes)
        row_list_header.addWidget(self.btn_autofill)

        layout.addLayout(row_list_header)

        # -------------------------------------------------------------
        # Section 5: Text Area for codes
        # -------------------------------------------------------------
        self.codes_edit = QPlainTextEdit()
        self.codes_edit.setFixedHeight(120)
        self.codes_edit.textChanged.connect(self._on_codes_changed)
        layout.addWidget(self.codes_edit)

        # Studio Boss Notification Detection Card (Glassmorphic Emerald)
        self.boss_card = QFrame()
        self.boss_card.setObjectName("bossCard")
        self.boss_card.setVisible(False)
        boss_card_layout = QVBoxLayout(self.boss_card)
        boss_card_layout.setContentsMargins(12, 8, 12, 8)
        boss_card_layout.setSpacing(6)

        self.lbl_boss_title = QLabel("✨ ĐÃ NHẬN DIỆN TIN NHẮN TỪ BOSS / WEB")
        self.lbl_boss_title.setObjectName("bossTitle")
        boss_card_layout.addWidget(self.lbl_boss_title)

        self.lbl_boss_info = QLabel()
        self.lbl_boss_info.setObjectName("bossInfo")
        self.lbl_boss_info.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_boss_info.setWordWrap(True)
        boss_card_layout.addWidget(self.lbl_boss_info)

        row_boss_options = QHBoxLayout()
        row_boss_options.setSpacing(12)
        self.chk_raw_folder = QCheckBox("Gom tất cả vào thư mục 'raw chọn'")
        self.chk_raw_folder.setChecked(True)
        self.chk_txt_summary = QCheckBox("Tạo file TXT phân loại (ảnh lớn, ảnh bàn...)")
        self.chk_txt_summary.setChecked(True)
        self.chk_customer_folder = QCheckBox("Tạo thư mục khách")
        self.chk_customer_folder.setChecked(True)
        self.chk_subfolders = QCheckBox("Chia vào các thư mục con")
        self.chk_subfolders.setChecked(False)

        self.chk_raw_folder.toggled.connect(self._on_raw_folder_toggled)
        self.chk_subfolders.toggled.connect(self._on_subfolders_toggled)

        row_boss_options.addWidget(self.chk_raw_folder)
        row_boss_options.addWidget(self.chk_txt_summary)
        row_boss_options.addWidget(self.chk_customer_folder)
        row_boss_options.addWidget(self.chk_subfolders)
        row_boss_options.addStretch()
        boss_card_layout.addLayout(row_boss_options)

        layout.addWidget(self.boss_card)

        # In-place Studio Guide Card
        self.guide_card = QFrame()
        self.guide_card.setObjectName("guideCard")
        card_layout = QVBoxLayout(self.guide_card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)

        self.lbl_guide_tip = QLabel()
        self.lbl_guide_tip.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_guide_tip.setWordWrap(True)
        self.lbl_guide_tip.setStyleSheet("font-size: 11px; color: #C5B6B8; line-height: 135%;")
        card_layout.addWidget(self.lbl_guide_tip)

        row_guide_btn = QHBoxLayout()
        row_guide_btn.setContentsMargins(0, 0, 0, 0)
        row_guide_btn.addStretch()
        btn_open_guide_inline = QPushButton("📖 Xem hướng dẫn chi tiết »")
        btn_open_guide_inline.setProperty("class", "guideLinkBtn")
        btn_open_guide_inline.clicked.connect(self._open_guide)
        row_guide_btn.addWidget(btn_open_guide_inline)
        card_layout.addLayout(row_guide_btn)

        layout.addWidget(self.guide_card)
        self._on_match_mode_changed()
        layout.addSpacing(3)

        # -------------------------------------------------------------
        # Section 6: Chế độ xử lý (Segmented Tabs)
        # -------------------------------------------------------------
        row_mode_label = QHBoxLayout()
        lbl_action_mode = QLabel("Thao tác khi lọc:")
        lbl_action_mode.setStyleSheet("font-size: 12px; font-weight: 700; color: #D5C7C9;")
        row_mode_label.addWidget(lbl_action_mode)

        self.chk_general_raw_folder = QCheckBox("Gom vào thư mục 'raw chọn'")
        self.chk_general_raw_folder.setChecked(True)
        self.recursive_check = QCheckBox("Quét cả thư mục con")
        self.recursive_check.setChecked(True)
        row_mode_label.addStretch()
        row_mode_label.addWidget(self.chk_general_raw_folder)
        row_mode_label.addWidget(self.recursive_check)
        layout.addLayout(row_mode_label)

        mode_container = QWidget()
        mode_container.setObjectName("modeContainer")
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(4, 3, 4, 3)
        mode_layout.setSpacing(6)

        self.mode_group = QButtonGroup(self)
        self.tab_copy = QPushButton("Sao chép (Khuyên dùng)")
        self.tab_copy.setProperty("class", "modeTab")
        self.tab_copy.setCheckable(True)
        self.tab_copy.setChecked(True)

        self.tab_move = QPushButton("Di chuyển")
        self.tab_move.setProperty("class", "modeTab")
        self.tab_move.setCheckable(True)

        self.tab_rename = QPushButton("Đổi tên theo mã")
        self.tab_rename.setProperty("class", "modeTab")
        self.tab_rename.setCheckable(True)

        self.mode_group.addButton(self.tab_copy, 0)
        self.mode_group.addButton(self.tab_move, 1)
        self.mode_group.addButton(self.tab_rename, 2)

        mode_layout.addWidget(self.tab_copy)
        mode_layout.addWidget(self.tab_move)
        mode_layout.addWidget(self.tab_rename)
        layout.addWidget(mode_container)

        # Progress bar (smooth thin bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "min-height: 6px; max-height: 6px; border-radius: 3px; background: #261B1C;"
        )
        layout.addWidget(self.progress_bar)
        layout.addSpacing(6)

        # -------------------------------------------------------------
        # Section 7: Big CTA Filter Button ("Tiến hành lọc")
        # -------------------------------------------------------------
        self.btn_filter = QPushButton("   Tiến hành lọc")
        self.btn_filter.setObjectName("primaryFilterButton")
        self.btn_filter.setIcon(self._get_icon("filter.svg"))
        self.btn_filter.setIconSize(QSize(22, 22))
        self.btn_filter.clicked.connect(self._on_filter_click)
        layout.addWidget(self.btn_filter)

        # Status Bar
        self.statusBar().showMessage("Sẵn sàng • KATISTUDIO v2.1")

    def _get_current_operation(self) -> str:
        checked_id = self.mode_group.checkedId()
        if checked_id == 1:
            return "move"
        if checked_id == 2:
            return "rename"
        return "copy"

    def _open_ai_visual_match(self) -> None:
        src_text = self.source_input.text().strip()
        dest_text = self.dest_input.text().strip()
        src_path = Path(src_text) if src_text and Path(src_text).exists() else None
        dest_path = Path(dest_text) if dest_text and Path(dest_text).exists() else None
        dialog = VisualMatchDialog(default_source_dir=src_path, default_dest_dir=dest_path, parent=self)
        dialog.exec()

    def _open_facebook_page(self) -> None:
        url = "https://www.facebook.com/katiphotographer/"
        try:
            if not QDesktopServices.openUrl(QUrl(url)):
                webbrowser.open(url)
        except Exception:
            webbrowser.open(url)

    def _open_guide(self) -> None:
        dialog = GuideDialog(self)
        dialog.exec()

    def _on_match_mode_changed(self) -> None:
        mode = self.match_mode_combo.currentData()
        if mode == MODE_LAST_4_DIGITS:
            self.codes_edit.setPlaceholderText(
                "Nhập 4 số cuối của ảnh (mỗi dòng một số)\n"
                "Ví dụ:\n"
                "1234\n"
                "0567\n"
                "8901\n"
                "0042"
            )
            self.lbl_guide_tip.setText(
                "🌟 <b>Chế độ 4 số cuối (Khuyên dùng):</b> Gõ <code>1234</code> → Tự động khớp chính xác <code>IMG_1234.CR3</code>, <code>_MG_1234.JPG</code>, <code>DSC_1234.ARW</code>.<br>"
                "<i>Tránh nhầm với ảnh 5 số (như IMG_12345.JPG). Dán trực tiếp từ Excel, Zalo...</i>"
            )
        elif mode == MODE_TRAILING_DIGITS:
            self.codes_edit.setPlaceholderText(
                "Nhập số cuối của ảnh (mỗi dòng một số)\n"
                "Ví dụ:\n"
                "42\n"
                "105\n"
                "1234"
            )
            self.lbl_guide_tip.setText(
                "🔢 <b>Chế độ số cuối linh hoạt:</b> Gõ <code>42</code> → Khớp <code>IMG_0042</code>, <code>DSC_0042</code>.<br>"
                "<i>Khớp mọi dãy số ở cuối tên ảnh không phụ thuộc số lượng chữ số 0.</i>"
            )
        elif mode == MODE_CONTAINS:
            self.codes_edit.setPlaceholderText(
                "Nhập chuỗi ký tự cần tìm (mỗi dòng một mã)\n"
                "Ví dụ:\n"
                "IMG_001\n"
                "DSC_5678\n"
                "KATI"
            )
            self.lbl_guide_tip.setText(
                "🔍 <b>Chế độ có chứa ký tự:</b> Tìm ảnh có tên chứa cụm từ đã nhập ở bất kỳ vị trí nào.<br>"
                "<i>Mỗi mã một dòng hoặc phân cách bằng dấu phẩy.</i>"
            )
        elif mode == MODE_EXACT:
            self.codes_edit.setPlaceholderText(
                "Nhập tên file chính xác (mỗi dòng một tên)\n"
                "Ví dụ:\n"
                "IMG_001.JPG\n"
                "_MG_1234.CR3\n"
                "DSC_5678.ARW"
            )
            self.lbl_guide_tip.setText(
                "🎯 <b>Chế độ tên chính xác:</b> So khớp chính xác 100% tên file gốc.<br>"
                "<i>Có thể kèm hoặc không kèm đuôi file mở rộng.</i>"
            )
        elif mode == MODE_STARTS_WITH:
            self.codes_edit.setPlaceholderText(
                "Nhập tiền tố bắt đầu (mỗi dòng một mã)\n"
                "Ví dụ:\n"
                "IMG_\n"
                "_MG_\n"
                "KATI_"
            )
            self.lbl_guide_tip.setText(
                "⏮ <b>Chế độ bắt đầu bằng:</b> Lọc các ảnh có tên bắt đầu bằng chuỗi ký tự đã nhập."
            )
        elif mode == MODE_ENDS_WITH:
            self.codes_edit.setPlaceholderText(
                "Nhập hậu tố kết thúc (mỗi dòng một mã)\n"
                "Ví dụ:\n"
                "_edit\n"
                "_retouch\n"
                "_final"
            )
            self.lbl_guide_tip.setText(
                "⏭ <b>Chế độ kết thúc bằng:</b> Lọc các ảnh có tên kết thúc bằng chuỗi ký tự đã nhập."
            )

    def _select_directory(self, target_line: QLineEdit) -> None:
        start_dir = target_line.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Chọn thư mục", start_dir)
        if selected:
            target_line.setText(selected)
            self._save_settings()

    def _paste_from_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text or not text.strip():
            QMessageBox.information(
                self,
                "Bộ nhớ tạm trống",
                "Chưa có nội dung văn bản trong bộ nhớ tạm (Clipboard).\nVui lòng sao chép (Copy) tin nhắn từ Boss hoặc nhóm Zalo trước khi bấm nút này.",
            )
            return

        self.codes_edit.setPlainText(text)
        self._on_codes_changed()

    def _on_codes_changed(self) -> None:
        raw_text = self.codes_edit.toPlainText()
        parsed = parse_selection_message(raw_text)
        self.parsed_message = parsed

        if parsed.is_structured and parsed.groups:
            self.boss_card.setVisible(True)
            self.lbl_boss_title.setText("✨ ĐÃ NHẬN DIỆN TIN NHẮN TỪ BOSS / WEB")

            cust_text = f"👤 Khách: <b>{parsed.customer_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; " if parsed.customer_name else ""
            groups_text = " &nbsp;•&nbsp; ".join(
                f"📁 <b>{g.name}</b> ({len(g.codes)} ảnh)" for g in parsed.groups
            )
            self.lbl_boss_info.setText(f"{cust_text}{groups_text}")

            if parsed.customer_name:
                self.chk_customer_folder.setText(f"Tạo thư mục khách ({parsed.customer_name})")
                self.chk_customer_folder.setVisible(True)
            else:
                self.chk_customer_folder.setVisible(False)

            total_codes = parsed.total_codes_count
            cust_label = f" • Khách: {parsed.customer_name}" if parsed.customer_name else ""
            self.statusBar().showMessage(
                f"Đã nhận diện: {len(parsed.groups)} nhóm • {total_codes} mã ảnh{cust_label}"
            )
        else:
            self.boss_card.setVisible(False)
            codes = normalize_codes(raw_text)
            count = len(codes)
            self.statusBar().showMessage(f"Đã nhập {count} mã ảnh" if count else "Sẵn sàng • KATISTUDIO")

    def _on_raw_folder_toggled(self, checked: bool) -> None:
        if checked and self.chk_subfolders.isChecked():
            self.chk_subfolders.setChecked(False)

    def _on_subfolders_toggled(self, checked: bool) -> None:
        if checked and self.chk_raw_folder.isChecked():
            self.chk_raw_folder.setChecked(False)

    def _autofill_codes(self) -> None:
        src = self.source_input.text().strip()
        if not src:
            QMessageBox.warning(self, "Chưa chọn thư mục", "Vui lòng chọn Nơi chứa file gốc trước khi điền tự động.")
            return

        source_path = Path(src)
        if not source_path.is_dir():
            QMessageBox.warning(self, "Lỗi thư mục", "Thư mục nguồn không tồn tại.")
            return

        try:
            files = scan_images(
                source_path,
                recursive=self.recursive_check.isChecked(),
                extension=self.format_combo.currentData(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi quét file", str(e))
            return

        if not files:
            QMessageBox.information(self, "Không tìm thấy ảnh", "Không tìm thấy file ảnh phù hợp trong thư mục nguồn.")
            return

        current_text = self.codes_edit.toPlainText().strip()
        if current_text:
            ans = QMessageBox.question(
                self,
                "Xác nhận thay thế",
                f"Đã tìm thấy {len(files)} ảnh trong thư mục.\nThay thế danh sách mã hiện tại bằng danh sách này?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        file_stems = [f.stem for f in files]
        self.codes_edit.setPlainText("\n".join(file_stems))
        self.statusBar().showMessage(f"Đã điền tự động {len(files)} mã ảnh từ thư mục gốc")

    def _on_filter_click(self) -> None:
        if self.thread and self.thread.isRunning():
            return

        src = self.source_input.text().strip()
        dst = self.dest_input.text().strip()
        raw_codes = self.codes_edit.toPlainText()

        if not src:
            QMessageBox.warning(self, "Chưa chọn nguồn", "Vui lòng chọn Nơi chứa file gốc.")
            return
        if not dst:
            QMessageBox.warning(self, "Chưa chọn đích", "Vui lòng chọn Nơi lưu file sau khi lọc.")
            return
        if Path(src).resolve() == Path(dst).resolve():
            QMessageBox.warning(self, "Thư mục trùng nhau", "Thư mục nguồn và đích không được trùng nhau.")
            return

        codes = normalize_codes(raw_codes)
        if not codes:
            QMessageBox.warning(self, "Chưa nhập mã", "Vui lòng nhập danh sách mã ảnh cần lọc (mỗi dòng 1 mã).")
            return

        self._set_busy(True, "Đang quét và đối chiếu ảnh...")
        self.cancel_event = Event()

        is_struct = bool(self.parsed_message and self.parsed_message.is_structured)
        if is_struct:
            use_single_raw = self.chk_raw_folder.isChecked()
            create_subfolders = self.chk_subfolders.isChecked()
            create_txt = self.chk_txt_summary.isChecked()
            cust_folder = (
                self.parsed_message.customer_name
                if (self.chk_customer_folder.isChecked() and self.parsed_message.customer_name)
                else ""
            )
        else:
            use_single_raw = self.chk_general_raw_folder.isChecked()
            create_subfolders = False
            create_txt = False
            cust_folder = ""

        worker = FilterWorker(
            Path(src),
            Path(dst),
            raw_codes,
            self._get_current_operation(),
            self.format_combo.currentData(),
            self.recursive_check.isChecked(),
            match_mode=self.match_mode_combo.currentData(),
            create_category_subfolders=create_subfolders,
            use_single_raw_folder=use_single_raw,
            raw_folder_name="raw chọn",
            create_txt_classification=create_txt,
            customer_folder=cust_folder,
            cancel_event=self.cancel_event,
        )
        self._run_worker(worker, is_preview=True)

    def _run_worker(self, worker: FilterWorker, *, is_preview: bool) -> None:
        self.worker = worker
        self.thread = QThread(self)
        worker.moveToThread(self.thread)

        self.thread.started.connect(worker.run)
        worker.failed.connect(self._on_worker_failed)

        if is_preview:
            worker.preview_ready.connect(self._on_preview_ready)
            worker.preview_ready.connect(self.thread.quit)
        else:
            worker.item_progress.connect(self._on_item_progress)
            worker.finished.connect(self._on_execution_finished)
            worker.finished.connect(self.thread.quit)

        worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(worker.deleteLater)
        self.thread.finished.connect(self._on_worker_cleaned)
        self.thread.start()

    def _on_preview_ready(self, items: list[TransferItem], scanned: int, code_count: int) -> None:
        self._set_busy(False)
        self.preview_items = items

        if not items:
            QMessageBox.information(
                self,
                "Không tìm thấy ảnh khớp",
                f"Đã quét {scanned} file trong thư mục nguồn nhưng không có ảnh nào khớp với {code_count} mã đã nhập.",
            )
            return

        # Show elegant Results Dialog
        dialog = ResultsDialog(
            items,
            self._get_current_operation(),
            Path(self.source_input.text()),
            Path(self.dest_input.text()),
            self,
        )

        if dialog.exec() == ResultsDialog.DialogCode.Accepted and dialog.confirmed:
            self._execute_transfer(items)

    def _execute_transfer(self, items: list[TransferItem]) -> None:
        self._set_busy(True, "Đang tiến hành xử lý ảnh...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_event = Event()

        is_struct = bool(self.parsed_message and self.parsed_message.is_structured)
        if is_struct:
            use_single_raw = self.chk_raw_folder.isChecked()
            create_subfolders = self.chk_subfolders.isChecked()
            create_txt = self.chk_txt_summary.isChecked()
            cust_folder = (
                self.parsed_message.customer_name
                if (self.chk_customer_folder.isChecked() and self.parsed_message.customer_name)
                else ""
            )
        else:
            use_single_raw = self.chk_general_raw_folder.isChecked()
            create_subfolders = False
            create_txt = False
            cust_folder = ""

        worker = FilterWorker(
            Path(self.source_input.text()),
            Path(self.dest_input.text()),
            self.codes_edit.toPlainText(),
            self._get_current_operation(),
            self.format_combo.currentData(),
            self.recursive_check.isChecked(),
            match_mode=self.match_mode_combo.currentData(),
            create_category_subfolders=create_subfolders,
            use_single_raw_folder=use_single_raw,
            raw_folder_name="raw chọn",
            create_txt_classification=create_txt,
            customer_folder=cust_folder,
            execute=True,
            items=items,
            cancel_event=self.cancel_event,
        )
        self._run_worker(worker, is_preview=False)

    def _on_item_progress(self, current: int, total: int, item: TransferItem) -> None:
        pct = round(current * 100 / total) if total else 0
        self.progress_bar.setValue(pct)
        self.statusBar().showMessage(f"Đang xử lý {current}/{total}: {item.filename}")

    def _on_execution_finished(self, items: list[TransferItem]) -> None:
        self._set_busy(False)
        self.progress_bar.setVisible(False)
        self.last_items = items

        success = sum(1 for i in items if i.status in {TransferStatus.COPIED, TransferStatus.MOVED, TransferStatus.RENAMED})
        failed = sum(1 for i in items if i.status == TransferStatus.FAILED)
        skipped = sum(1 for i in items if i.status == TransferStatus.SKIPPED)

        dest_dir = Path(self.dest_input.text())

        msg = QMessageBox(self)
        msg.setWindowTitle("Hoàn tất xử lý")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Đã xử lý xong {len(items)} file ảnh!")

        info_lines = [
            f"• Thành công: {success} file",
            f"• Lỗi: {failed} file",
            f"• Bỏ qua / Hủy: {skipped} file",
        ]
        if any(item.category for item in items):
            info_lines.append("• Đã tạo file: danh_sach_chon_anh.txt (ghi rõ ảnh lớn, ảnh bàn...)")
        info_lines.append(f"\nĐã lưu tại: {dest_dir}")
        msg.setInformativeText("\n".join(info_lines))

        btn_open = msg.addButton("Mở thư mục", QMessageBox.ButtonRole.ActionRole)
        btn_report = msg.addButton("Xuất báo cáo", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Đóng", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        if msg.clickedButton() == btn_open:
            if dest_dir.exists():
                os.startfile(str(dest_dir))
        elif msg.clickedButton() == btn_report:
            try:
                csv_path, json_path = export_report(
                    items,
                    dest_dir,
                    source_dir=Path(self.source_input.text()),
                    destination_dir=dest_dir,
                    operation=self._get_current_operation(),
                )
                QMessageBox.information(self, "Đã xuất báo cáo", f"Lưu thành công:\n{csv_path.name}")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi xuất báo cáo", str(e))

        self.statusBar().showMessage(f"Hoàn tất: {success} thành công • KATISTUDIO")

    def _on_worker_failed(self, error: str) -> None:
        self._set_busy(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Lỗi thực hiện", f"Đã xảy ra lỗi:\n{error}")
        self.statusBar().showMessage("Có lỗi xảy ra")

    def _on_worker_cleaned(self) -> None:
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.source_input.setEnabled(not busy)
        self.dest_input.setEnabled(not busy)
        self.btn_source.setEnabled(not busy)
        self.btn_dest.setEnabled(not busy)
        self.format_combo.setEnabled(not busy)
        self.match_mode_combo.setEnabled(not busy)
        self.btn_autofill.setEnabled(not busy)
        self.codes_edit.setEnabled(not busy)
        self.btn_filter.setEnabled(not busy)
        if message:
            self.statusBar().showMessage(message)

    def _restore_settings(self) -> None:
        self.source_input.setText(self.settings.value("source_dir", "", type=str))
        self.dest_input.setText(self.settings.value("destination_dir", "", type=str))
        self.recursive_check.setChecked(self.settings.value("recursive", True, type=bool))
        op_idx = self.settings.value("operation_idx", 0, type=int)
        if op_idx == 1:
            self.tab_move.setChecked(True)
        elif op_idx == 2:
            self.tab_rename.setChecked(True)
        else:
            self.tab_copy.setChecked(True)

    def _save_settings(self) -> None:
        self.settings.setValue("source_dir", self.source_input.text())
        self.settings.setValue("destination_dir", self.dest_input.text())
        self.settings.setValue("recursive", self.recursive_check.isChecked())
        self.settings.setValue("operation_idx", self.mode_group.checkedId())
