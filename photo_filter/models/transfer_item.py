from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TransferStatus(str, Enum):
    PENDING = "Chờ xử lý"
    READY = "Sẵn sàng"
    COPIED = "Đã sao chép"
    MOVED = "Đã di chuyển"
    RENAMED = "Đã đổi tên"
    SKIPPED = "Đã bỏ qua"
    CONFLICT = "Trùng tên"
    FAILED = "Lỗi"


@dataclass
class TransferItem:
    source: Path
    matched_code: str
    destination: Path | None = None
    status: TransferStatus = TransferStatus.PENDING
    error: str = ""
    category: str = ""

    @property
    def filename(self) -> str:
        return self.source.name

    def as_dict(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "matched_code": self.matched_code,
            "category": self.category,
            "destination": str(self.destination or ""),
            "status": self.status.value,
            "error": self.error,
        }
