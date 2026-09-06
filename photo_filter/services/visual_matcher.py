from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import imagehash
from PIL import Image
from PySide6.QtCore import QThread, Signal

RAW_EXTENSIONS = {".arw", ".cr2", ".cr3", ".nef", ".raf", ".dng"}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    *RAW_EXTENSIONS,
}

# Distance threshold: Hamming distance <= 12 is generally an excellent perceptual match
DEFAULT_MATCH_THRESHOLD = 12


def get_image_hash(file_path: Path) -> imagehash.ImageHash:
    """Compute perceptual hash (phash) for a RAW or standard photo."""
    ext = file_path.suffix.lower()

    if ext in RAW_EXTENSIONS:
        try:
            import rawpy

            with rawpy.imread(str(file_path)) as raw:
                # Fast processing: half_size=True makes it 4x faster with identical perceptual layout
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=True,
                    no_auto_bright=True,
                )
                img = Image.fromarray(rgb)
                return imagehash.phash(img)
        except Exception:
            # Fallback to standard Image.open if rawpy fails or plugin handles it
            with Image.open(file_path) as img:
                return imagehash.phash(img)
    else:
        with Image.open(file_path) as img:
            return imagehash.phash(img)


@dataclass
class VisualMatchItem:
    sample_path: Path
    best_match_path: Path | None = None
    best_distance: int = 999
    is_matched: bool = False
    confidence_percent: int = 0
    destination_path: Path | None = None

    @property
    def sample_name(self) -> str:
        return self.sample_path.name

    @property
    def matched_name(self) -> str:
        return self.best_match_path.name if self.best_match_path else "—"


class VisualMatchWorker(QThread):
    """Background worker that scans camera RAW/JPG files and matches with client screenshots."""

    progress = Signal(int, int, str)  # current, total, message
    item_matched = Signal(object)  # VisualMatchItem
    finished = Signal(list, int, int)  # items, found_count, not_found_count
    failed = Signal(str)

    def __init__(
        self,
        sample_paths: list[Path],
        source_dir: Path,
        destination_dir: Path,
        threshold: int = DEFAULT_MATCH_THRESHOLD,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sample_paths = sample_paths
        self.source_dir = source_dir
        self.destination_dir = destination_dir
        self.threshold = threshold
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            total_samples = len(self.sample_paths)
            if total_samples == 0:
                self.finished.emit([], 0, 0)
                return

            self.progress.emit(0, total_samples, "Đang phân tích mã hash các ảnh chụp màn hình...")

            # 1. Compute hashes for sample screenshot images
            sample_entries: list[dict] = []
            for idx, p in enumerate(self.sample_paths, 1):
                if self._is_cancelled:
                    return
                try:
                    h = get_image_hash(p)
                    sample_entries.append({
                        "path": p,
                        "hash": h,
                        "best_path": None,
                        "best_dist": 999,
                    })
                except Exception:
                    sample_entries.append({
                        "path": p,
                        "hash": None,
                        "best_path": None,
                        "best_dist": 999,
                    })
                self.progress.emit(idx, total_samples, f"Đã băm ảnh mẫu {idx}/{total_samples}: {p.name}")

            # 2. Gather source files in source_dir (RAW + JPG)
            source_files: list[Path] = []
            for root, _, files in os.walk(self.source_dir):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in IMAGE_EXTENSIONS:
                        source_files.append(Path(root) / f)

            total_sources = len(source_files)
            if total_sources == 0:
                self.failed.emit("Không tìm thấy file ảnh (RAW/JPG) nào trong thư mục nguồn!")
                return

            self.progress.emit(0, total_sources, f"Đang soi kỹ {total_sources} file gốc để đối chiếu...")

            # 3. Compare hashes
            for src_idx, src_path in enumerate(source_files, 1):
                if self._is_cancelled:
                    return

                try:
                    src_hash = get_image_hash(src_path)
                    for entry in sample_entries:
                        if entry["hash"] is None:
                            continue
                        dist = src_hash - entry["hash"]
                        if dist < entry["best_dist"]:
                            entry["best_dist"] = dist
                            entry["best_path"] = src_path
                except Exception:
                    continue

                if src_idx % 5 == 0 or src_idx == total_sources:
                    self.progress.emit(
                        src_idx,
                        total_sources,
                        f"Đang đối chiếu: {src_idx}/{total_sources} file gốc ({src_path.name})",
                    )

            # 4. Organize into destinations
            found_folder = self.destination_dir / "ẢNH CHỌN RAW"
            not_found_folder = self.destination_dir / "ẢNH CHƯA TÌM THẤY"
            found_folder.mkdir(parents=True, exist_ok=True)
            not_found_folder.mkdir(parents=True, exist_ok=True)

            items: list[VisualMatchItem] = []
            count_found = 0
            count_not_found = 0

            for entry in sample_entries:
                best_dist = entry["best_dist"]
                best_path = entry["best_path"]
                is_match = (best_dist <= self.threshold) and (best_path is not None)

                # Confidence calculation: 0 distance -> 100%, distance=12 -> ~40%
                conf = max(0, min(100, 100 - best_dist * 5)) if best_dist < 900 else 0

                item = VisualMatchItem(
                    sample_path=entry["path"],
                    best_match_path=best_path,
                    best_distance=best_dist,
                    is_matched=is_match,
                    confidence_percent=conf,
                )

                if is_match and best_path:
                    dest_file = found_folder / best_path.name
                    shutil.copy2(best_path, dest_file)
                    item.destination_path = dest_file
                    count_found += 1
                else:
                    dest_sample = not_found_folder / entry["path"].name
                    shutil.copy2(entry["path"], dest_sample)
                    item.destination_path = dest_sample
                    count_not_found += 1

                items.append(item)
                self.item_matched.emit(item)

            self.finished.emit(items, count_found, count_not_found)

        except Exception as e:
            self.failed.emit(str(e))
