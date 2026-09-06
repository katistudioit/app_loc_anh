from __future__ import annotations

import re
import shutil
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from photo_filter.models.transfer_item import TransferItem, TransferStatus

Operation = str
ProgressCallback = Callable[[int, int, TransferItem], None]
CancelCheck = Callable[[], bool]

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_filename(value: str) -> str:
    cleaned = _INVALID_FILENAME.sub("_", value).strip(" .")
    if not cleaned:
        return "image"
    if cleaned.upper() in _RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned


def safe_folder_name(value: str) -> str:
    cleaned = _INVALID_FILENAME.sub("_", value).strip(" .")
    if not cleaned:
        return "Nhóm ảnh"
    if cleaned.upper() in _RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned


def plan_operations(
    items: Iterable[TransferItem],
    destination_dir: Path,
    operation: Operation,
    *,
    create_category_subfolders: bool = False,
    use_single_raw_folder: bool = False,
    raw_folder_name: str = "raw chọn",
    customer_folder: str = "",
) -> list[TransferItem]:
    destination_dir = destination_dir.expanduser().resolve()
    if customer_folder and customer_folder.strip():
        destination_dir = destination_dir / safe_folder_name(customer_folder.strip())
    destination_dir.mkdir(parents=True, exist_ok=True)

    if use_single_raw_folder:
        folder_label = raw_folder_name.strip() if raw_folder_name and raw_folder_name.strip() else "raw chọn"
        single_dest_dir = destination_dir / safe_folder_name(folder_label)
        single_dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        single_dest_dir = destination_dir

    planned: list[TransferItem] = []
    reserved: set[Path] = set()
    source_to_target: dict[Path, Path] = {}

    for item in items:
        resolved_src = item.source.resolve()

        if use_single_raw_folder:
            item_dest_dir = single_dest_dir
            # If the exact same file is selected across multiple categories, keep single file in folder
            if resolved_src in source_to_target:
                item.destination = source_to_target[resolved_src]
                item.status = TransferStatus.READY
                item.error = ""
                planned.append(item)
                continue
        elif create_category_subfolders and item.category:
            item_dest_dir = destination_dir / safe_folder_name(item.category)
            item_dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            item_dest_dir = destination_dir

        if operation == "rename":
            base = Path(item.matched_code).stem if Path(item.matched_code).suffix else item.matched_code
            filename = f"{safe_filename(base)}{item.source.suffix.lower()}"
        else:
            filename = item.source.name

        target = unique_destination(item_dest_dir / filename, reserved)
        reserved.add(target)
        source_to_target[resolved_src] = target
        item.destination = target
        item.status = TransferStatus.READY
        item.error = ""
        planned.append(item)

    return planned


def execute_operations(
    items: Iterable[TransferItem],
    operation: Operation,
    *,
    progress: ProgressCallback | None = None,
    is_cancelled: CancelCheck | None = None,
) -> list[TransferItem]:
    planned = list(items)
    total = len(planned)

    # Track how many times each source file is referenced
    source_counts: dict[Path, int] = {}
    for item in planned:
        resolved_src = item.source.resolve()
        source_counts[resolved_src] = source_counts.get(resolved_src, 0) + 1

    already_transferred: set[Path] = set()

    for index, item in enumerate(planned, start=1):
        if is_cancelled and is_cancelled():
            item.status = TransferStatus.SKIPPED
            item.error = "Đã hủy bởi người dùng"
            if progress:
                progress(index, total, item)
            continue
        if not item.destination:
            item.status = TransferStatus.FAILED
            item.error = "Thiếu đường dẫn đích"
            if progress:
                progress(index, total, item)
            continue
        if item.source.resolve() == item.destination.resolve():
            item.status = TransferStatus.SKIPPED
            item.error = "Nguồn và đích là cùng một file"
            if progress:
                progress(index, total, item)
            continue

        # If already transferred to this exact destination (e.g. multi-category shared file)
        if item.destination in already_transferred:
            if operation == "copy":
                item.status = TransferStatus.COPIED
            elif operation == "move":
                item.status = TransferStatus.MOVED
            else:
                item.status = TransferStatus.RENAMED
            if progress:
                progress(index, total, item)
            continue

        try:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            resolved_src = item.source.resolve()
            remaining_refs = source_counts.get(resolved_src, 1)

            if operation == "copy":
                shutil.copy2(item.source, item.destination)
                item.status = TransferStatus.COPIED
                already_transferred.add(item.destination)
            elif operation in ("move", "rename"):
                # If this source is needed by another category later in the queue, copy instead of removing original!
                if remaining_refs > 1:
                    shutil.copy2(item.source, item.destination)
                    source_counts[resolved_src] = remaining_refs - 1
                    item.status = TransferStatus.MOVED if operation == "move" else TransferStatus.RENAMED
                else:
                    shutil.move(str(item.source), str(item.destination))
                    item.status = TransferStatus.MOVED if operation == "move" else TransferStatus.RENAMED
                already_transferred.add(item.destination)
            else:
                raise ValueError(f"Thao tác không được hỗ trợ: {operation}")
        except (OSError, shutil.Error, ValueError) as error:
            item.status = TransferStatus.FAILED
            item.error = str(error)

        if progress:
            progress(index, total, item)

    return planned


def generate_classification_content(
    items: Iterable[TransferItem],
    customer_name: str = "",
    folder_name: str = "raw chọn",
) -> str:
    """Generate structured TXT content specifying which photo is ẢNH LỚN, ẢNH BÀN, ALBUM..."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    item_list = list(items)

    # Unique files count
    unique_files: set[str] = set()
    categories: dict[str, list[str]] = {}
    file_to_categories: dict[str, list[str]] = {}

    for item in item_list:
        cat = item.category.strip() if item.category else "ẢNH CHỌN"
        fname = item.destination.name if item.destination else item.source.name
        unique_files.add(fname)

        if cat not in categories:
            categories[cat] = []
        if fname not in categories[cat]:
            categories[cat].append(fname)

        if fname not in file_to_categories:
            file_to_categories[fname] = []
        if cat not in file_to_categories[fname]:
            file_to_categories[fname].append(cat)

    total_count = len(unique_files) if unique_files else len(item_list)

    lines = [
        "=" * 68,
        "                    KATI STUDIO - DANH SÁCH ẢNH CHỌN",
        "=" * 68,
    ]
    if customer_name:
        lines.append(f"Khách hàng   : {customer_name}")
    lines.append(f"Thời gian tạo: {now_str}")
    lines.append(f"Tổng số ảnh  : {total_count} ảnh")
    if folder_name:
        lines.append(f"Thư mục lưu  : {folder_name}")
    lines.append("=" * 68)
    lines.append("")
    lines.append("--- PHÂN LOẠI THEO NHÓM IN ẤN / THIẾT KẾ ---")
    lines.append("")

    for cat, files in categories.items():
        lines.append(f"[{cat}] ({len(files)} ảnh):")
        for i, f in enumerate(files, 1):
            lines.append(f"  {i:2d}. {f}")
        lines.append("")

    lines.append("=" * 68)
    lines.append("--- CHI TIẾT TỪNG FILE ĐÃ CHỌN ---")
    for fname in sorted(file_to_categories.keys()):
        cats_str = ", ".join(file_to_categories[fname])
        lines.append(f"  • {fname:<30} --> [{cats_str}]")
    lines.append("=" * 68)
    lines.append("")

    return "\n".join(lines)


def write_classification_txt(
    destination_dir: Path,
    items: Iterable[TransferItem],
    customer_name: str = "",
    folder_name: str = "raw chọn",
    txt_filename: str = "danh_sach_chon_anh.txt",
) -> Path:
    """Save the classification TXT file to destination folder."""
    destination_dir = destination_dir.expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    out_file = destination_dir / txt_filename
    content = generate_classification_content(items, customer_name, folder_name)
    out_file.write_text(content, encoding="utf-8")
    return out_file


def unique_destination(candidate: Path, reserved: set[Path] | None = None) -> Path:
    reserved = reserved or set()
    candidate = candidate.resolve()
    if not candidate.exists() and candidate not in reserved:
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        alternative = candidate.with_name(f"{stem}_{counter:03d}{suffix}")
        if not alternative.exists() and alternative not in reserved:
            return alternative
        counter += 1
