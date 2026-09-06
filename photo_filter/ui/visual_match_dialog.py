from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from photo_filter.services.visual_matcher import VisualMatchItem, VisualMatchWorker


class VisualMatchDialog(QDialog):
    """Studio AI Visual Match Dialog - Find and match original RAW photos from client screenshots."""

    def __init__(self, default_source_dir: Path | None = None, default_dest_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("KATISTUDIO - Tìm ảnh từ ảnh chụp màn hình (AI Visual Match)")
        self.resize(780, 580)
        self.setMinimumSize(680, 480)

        self.sample_paths: list[Path] = []
        self.default_source_dir = default_source_dir
        self.default_dest_dir = default_dest_dir
        self.worker: VisualMatchWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🔍 TÌM ẢNH BẰNG HÌNH CHỤP MÀN HÌNH (AI)")
        title.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Dành cho trường hợp khách không ghi mã mà chụp màn hình điện thoại gửi qua Zalo / Facebook")
        subtitle.setStyleSheet("font-size: 12px; color: #9A8A8C;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setProperty("class", "pillButton")
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Step 1: Chọn ảnh chụp màn hình khách gửi
        lbl_step1 = QLabel("1. Danh sách ảnh chụp màn hình khách gửi:")
        lbl_step1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FF9800;")
        layout.addWidget(lbl_step1)

        row_samples = QHBoxLayout()
        self.lbl_samples_count = QLabel("Chưa chọn ảnh chụp màn hình nào")
        self.lbl_samples_count.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.25); border: 1.2px solid rgba(255, 255, 255, 0.3); "
            "border-radius: 8px; padding: 8px 12px; color: #FFFFFF; font-size: 12px;"
        )
        row_samples.addWidget(self.lbl_samples_count, 1)

        self.btn_pick_samples = QPushButton("Chọn ảnh khách...")
        self.btn_pick_samples.setProperty("class", "dialogAction")
        self.btn_pick_samples.clicked.connect(self._pick_samples)
        row_samples.addWidget(self.btn_pick_samples)
        layout.addLayout(row_samples)

        # Step 2: Thư mục ảnh gốc (RAW hoặc JPG)
        lbl_step2 = QLabel("2. Thư mục chứa file gốc máy ảnh (RAW / JPG):")
        lbl_step2.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(lbl_step2)

        row_source = QHBoxLayout()
        self.input_source = QLineEdit()
        self.input_source.setPlaceholderText("Chưa chọn thư mục gốc máy ảnh")
        self.input_source.setReadOnly(True)
        if self.default_source_dir and self.default_source_dir.exists():
            self.input_source.setText(str(self.default_source_dir))
        row_source.addWidget(self.input_source, 1)

        self.btn_pick_source = QPushButton("Chọn...")
        self.btn_pick_source.setProperty("class", "dialogAction")
        self.btn_pick_source.clicked.connect(self._pick_source)
        row_source.addWidget(self.btn_pick_source)
        layout.addLayout(row_source)

        # Step 3: Thư mục lưu kết quả
        lbl_step3 = QLabel("3. Thư mục lưu kết quả (Tự động chia 'ẢNH CHỌN RAW' & 'ẢNH CHƯA TÌM THẤY'):")
        lbl_step3.setStyleSheet("font-size: 13px; font-weight: 700; color: #20B59B;")
        layout.addWidget(lbl_step3)

        row_dest = QHBoxLayout()
        self.input_dest = QLineEdit()
        self.input_dest.setPlaceholderText("Chưa chọn thư mục lưu kết quả")
        self.input_dest.setReadOnly(True)
        if self.default_dest_dir and self.default_dest_dir.exists():
            self.input_dest.setText(str(self.default_dest_dir))
        row_dest.addWidget(self.input_dest, 1)

        self.btn_pick_dest = QPushButton("Chọn...")
        self.btn_pick_dest.setProperty("class", "dialogAction")
        self.btn_pick_dest.clicked.connect(self._pick_dest)
        row_dest.addWidget(self.btn_pick_dest)
        layout.addLayout(row_dest)

        # Table for Results
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Ảnh chụp màn hình", "Ảnh RAW khớp", "Độ tin cậy", "Trạng thái"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Progress bar & Status
        self.status_label = QLabel("Sẵn sàng quét.")
        self.status_label.setStyleSheet("font-size: 12px; color: #EDE1E3;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("min-height: 8px; max-height: 8px; border-radius: 4px; background: #2A1F20;")
        layout.addWidget(self.progress_bar)

        # Bottom buttons
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_cancel = QPushButton("Đóng")
        self.btn_cancel.setProperty("class", "dialogAction")
        self.btn_cancel.clicked.connect(self._on_cancel)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_start = QPushButton("🚀 Bắt đầu gom ảnh AI")
        self.btn_start.setProperty("class", "dialogPrimary")
        self.btn_start.clicked.connect(self._start_matching)
        bottom_bar.addWidget(self.btn_start)

        layout.addLayout(bottom_bar)

    def _pick_samples(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "CHỌN TẤT CẢ ẢNH KHÁCH GỬI (ẢNH CHỤP MÀN HÌNH)",
            "",
            "Ảnh chụp màn hình (*.jpg *.jpeg *.png *.webp *.bmp);;Tất cả định dạng (*.*)",
        )
        if files:
            self.sample_paths = [Path(f) for f in files]
            self.lbl_samples_count.setText(f"✅ Đã chọn {len(self.sample_paths)} ảnh khách gửi")

    def _pick_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "CHỌN THƯ MỤC CHỨA FILE GỐC (RAW HOẶC JPG)")
        if folder:
            self.input_source.setText(folder)

    def _pick_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "CHỌN NƠI LƯU KẾT QUẢ")
        if folder:
            self.input_dest.setText(folder)

    def _start_matching(self) -> None:
        if not self.sample_paths:
            QMessageBox.warning(self, "Thiếu ảnh khách gửi", "Vui lòng bấm 'Chọn ảnh khách...' để nạp các ảnh chụp màn hình.")
            return

        source_text = self.input_source.text().strip()
        if not source_text or not Path(source_text).exists():
            QMessageBox.warning(self, "Thiếu thư mục gốc", "Vui lòng chọn thư mục chứa ảnh gốc máy ảnh.")
            return

        dest_text = self.input_dest.text().strip()
        if not dest_text:
            QMessageBox.warning(self, "Thiếu nơi lưu", "Vui lòng chọn thư mục để lưu kết quả.")
            return

        source_dir = Path(source_text)
        dest_dir = Path(dest_text)

        self.table.setRowCount(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_pick_samples.setEnabled(False)
        self.btn_pick_source.setEnabled(False)
        self.btn_pick_dest.setEnabled(False)

        self.worker = VisualMatchWorker(
            sample_paths=self.sample_paths,
            source_dir=source_dir,
            destination_dir=dest_dir,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.item_matched.connect(self._on_item_matched)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.status_label.setText(message)
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)

    def _on_item_matched(self, item: VisualMatchItem) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        c_sample = QTableWidgetItem(item.sample_name)
        c_matched = QTableWidgetItem(item.matched_name)
        c_conf = QTableWidgetItem(f"{item.confidence_percent}%" if item.is_matched else "—")
        status_str = "✅ Đã nhặt" if item.is_matched else "⚠️ Chưa tin cậy"
        c_status = QTableWidgetItem(status_str)

        if item.is_matched:
            c_matched.setForeground(QColor("#20B59B"))
            c_conf.setForeground(QColor("#20B59B"))
            c_status.setForeground(QColor("#20B59B"))
        else:
            c_matched.setForeground(QColor("#8C7B7D"))
            c_conf.setForeground(QColor("#FF9800"))
            c_status.setForeground(QColor("#FF5252"))

        self.table.setItem(row, 0, c_sample)
        self.table.setItem(row, 1, c_matched)
        self.table.setItem(row, 2, c_conf)
        self.table.setItem(row, 3, c_status)

    def _on_finished(self, items: list[VisualMatchItem], found_count: int, not_found_count: int) -> None:
        self.progress_bar.setVisible(False)
        self.btn_start.setEnabled(True)
        self.btn_pick_samples.setEnabled(True)
        self.btn_pick_source.setEnabled(True)
        self.btn_pick_dest.setEnabled(True)

        msg = f"✅ Đã nhặt chuẩn: {found_count} ảnh vào thư mục 'ẢNH CHỌN RAW'."
        if not_found_count > 0:
            msg += f"\n\n⚠️ Có {not_found_count} tấm chưa đủ độ tin cậy (đã lưu vào 'ẢNH CHƯA TÌM THẤY' để anh nhặt tay nhé!)."

        self.status_label.setText(f"Hoàn thành: {found_count} chuẩn, {not_found_count} nhặt tay.")
        QMessageBox.information(self, "KATI STUDIO - GOM ẢNH RAW PRO", msg)

    def _on_failed(self, error_msg: str) -> None:
        self.progress_bar.setVisible(False)
        self.btn_start.setEnabled(True)
        self.btn_pick_samples.setEnabled(True)
        self.btn_pick_source.setEnabled(True)
        self.btn_pick_dest.setEnabled(True)
        self.status_label.setText(f"Lỗi: {error_msg}")
        QMessageBox.critical(self, "LỖI AI", f"Không thể xử lý: {error_msg}")

    def _on_cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        self.reject()
