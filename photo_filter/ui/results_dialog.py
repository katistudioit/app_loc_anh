from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from photo_filter.models.transfer_item import TransferItem, TransferStatus
from photo_filter.services.report import export_report


class ResultsDialog(QDialog):
    def __init__(
        self,
        items: list[TransferItem],
        operation: str,
        source_dir: Path,
        destination_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.items = items
        self.operation = operation
        self.source_dir = source_dir
        self.destination_dir = destination_dir
        self.confirmed = False
        self._build_ui()

    def _build_ui(self) -> None:
        op_labels = {
            "copy": "Sao chép ảnh",
            "move": "Di chuyển ảnh",
            "rename": "Đổi tên theo mã",
        }
        self.setWindowTitle("KATISTUDIO - Kết quả đối chiếu ảnh")
        self.resize(840, 580)
        self.setMinimumSize(700, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        has_categories = any(bool(item.category) for item in self.items)

        # Header Title
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Kết quả quét & đối chiếu")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")

        sub_parts = [f"Thao tác: {op_labels.get(self.operation, self.operation)}", f"Thư mục đích: {self.destination_dir.name}"]
        if has_categories:
            unique_cats = list(dict.fromkeys(item.category for item in self.items if item.category))
            sub_parts.append(f"Nhóm: {', '.join(unique_cats)}")

        subtitle = QLabel(" • ".join(sub_parts))
        subtitle.setStyleSheet("font-size: 12px; color: #9A8A8C;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Stat cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        total_count = len(self.items)

        stats_layout.addWidget(self._create_stat_card("Tổng ảnh khớp", str(total_count), "#20B59B"))

        if has_categories:
            # Group stats breakdown
            cat_counts: dict[str, int] = {}
            for item in self.items:
                cat = item.category or "Khác"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            summary_cats = " • ".join(f"{k}: {v}" for k, v in cat_counts.items())
            stats_layout.addWidget(self._create_stat_card("Phân loại nhóm", summary_cats, "#FF9800"))
        else:
            stats_layout.addWidget(self._create_stat_card("Trạng thái", "Sẵn sàng", "#FFFFFF"))

        stats_layout.addWidget(self._create_stat_card("Chế độ", op_labels.get(self.operation, self.operation), "#FF5252"))
        layout.addLayout(stats_layout)

        # Table setup
        if has_categories:
            self.table = QTableWidget(len(self.items), 5)
            self.table.setHorizontalHeaderLabels(["Tên file gốc", "Mã khớp", "Nhóm / Mục", "Đích dự kiến", "Trạng thái"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        else:
            self.table = QTableWidget(len(self.items), 4)
            self.table.setHorizontalHeaderLabels(["Tên file gốc", "Mã khớp", "Tên đích dự kiến", "Trạng thái"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)

        for row, item in enumerate(self.items):
            cell_name = QTableWidgetItem(item.filename)
            cell_code = QTableWidgetItem(item.matched_code)

            # Determine destination display string
            dest_display = ""
            if item.destination:
                try:
                    dest_display = str(item.destination.relative_to(self.destination_dir))
                except ValueError:
                    dest_display = item.destination.name

            cell_dest = QTableWidgetItem(dest_display)
            cell_status = QTableWidgetItem(item.status.value)
            cell_status.setForeground(QColor("#20B59B"))

            if has_categories:
                cell_cat = QTableWidgetItem(item.category or "—")
                cell_cat.setForeground(QColor("#FFB74D"))  # Warm golden/amber for studio groups
                self.table.setItem(row, 0, cell_name)
                self.table.setItem(row, 1, cell_code)
                self.table.setItem(row, 2, cell_cat)
                self.table.setItem(row, 3, cell_dest)
                self.table.setItem(row, 4, cell_status)
            else:
                self.table.setItem(row, 0, cell_name)
                self.table.setItem(row, 1, cell_code)
                self.table.setItem(row, 2, cell_dest)
                self.table.setItem(row, 3, cell_status)

        layout.addWidget(self.table)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("min-height: 8px; max-height: 8px; border-radius: 4px; background: #2A1F20;")
        layout.addWidget(self.progress_bar)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_report = QPushButton("Xuất báo cáo (CSV/Excel)")
        self.btn_report.setProperty("class", "dialogAction")
        self.btn_report.clicked.connect(self._export_report)
        btn_layout.addWidget(self.btn_report)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Đóng")
        self.btn_cancel.setProperty("class", "dialogAction")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton(f"Thực hiện {op_labels.get(self.operation, self.operation)}")
        self.btn_confirm.setProperty("class", "dialogPrimary")
        self.btn_confirm.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "statCard")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(2)

        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {color};")
        lbl_val.setWordWrap(True)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #8C7B7D;")

        vbox.addWidget(lbl_val)
        vbox.addWidget(lbl_title)
        return card

    def _export_report(self) -> None:
        try:
            csv_path, json_path = export_report(
                self.items,
                self.destination_dir,
                source_dir=self.source_dir,
                destination_dir=self.destination_dir,
                operation=self.operation,
            )
            QMessageBox.information(
                self,
                "Đã xuất báo cáo",
                f"Báo cáo đã được lưu tại:\n- {csv_path.name}\n- {json_path.name}\n\nThư mục: {self.destination_dir}",
            )
        except OSError as e:
            QMessageBox.warning(self, "Lỗi xuất báo cáo", str(e))

    def _on_confirm(self) -> None:
        self.confirmed = True
        self.accept()
