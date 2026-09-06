from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

# Đầy đủ định dạng ảnh phổ biến và RAW máy ảnh chuyên nghiệp (Canon, Sony, Nikon, Fuji, Leica...)
IMAGE_EXTENSIONS = (
    # Standard formats
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
    ".avif",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".psd",
    ".psb",
    # Canon RAW
    ".cr2",
    ".cr3",
    ".crw",
    # Sony RAW
    ".arw",
    ".srf",
    ".sr2",
    # Nikon RAW
    ".nef",
    ".nrw",
    # Fujifilm RAW
    ".raf",
    # Panasonic / Lumix RAW
    ".rw2",
    # Olympus / OM System RAW
    ".orf",
    ".ori",
    # Universal / Leica / Adobe RAW
    ".dng",
    ".rwl",
    # Pentax RAW
    ".pef",
    ".ptx",
    # Hasselblad / Phase One / Sigma / Other
    ".3fr",
    ".fff",
    ".iiq",
    ".x3f",
    ".srw",
    ".erf",
    ".gpr",
    ".mef",
    ".mos",
    ".mrw",
    ".kdc",
    ".dcr",
)

IGNORE_SYSTEM_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}


def scan_images(
    source_dir: Path,
    *,
    recursive: bool = True,
    extension: str | tuple[str, ...] | None = None,
    exclude_dir: Path | None = None,
) -> list[Path]:
    """Return image files in deterministic path order."""
    source_dir = source_dir.expanduser().resolve()
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Thư mục nguồn không tồn tại: {source_dir}")

    if isinstance(extension, tuple):
        wanted_extensions = {item.lower() for item in extension}
    elif extension:
        wanted_extensions = {extension.lower()}
    else:
        wanted_extensions = None

    iterator: Iterable[Path] = source_dir.rglob("*") if recursive else source_dir.glob("*")
    files: list[Path] = []
    # Only exclude if exclude_dir is strictly a subdirectory inside source_dir
    resolved_exclude: Path | None = None
    if exclude_dir:
        candidate_exclude = exclude_dir.expanduser().resolve()
        if candidate_exclude != source_dir and _is_within(candidate_exclude, source_dir):
            resolved_exclude = candidate_exclude

    for path in iterator:
        if not path.is_file():
            continue
        if path.name.lower() in IGNORE_SYSTEM_FILES or path.name.startswith("._"):
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if wanted_extensions and path.suffix.lower() not in wanted_extensions:
            continue
        resolved_path = path.resolve()
        if resolved_exclude and _is_within(resolved_path, resolved_exclude):
            continue
        files.append(resolved_path)

    return sorted(files, key=lambda item: str(item).casefold())


def iter_image_files(source_dir: Path, **kwargs: object) -> Iterator[Path]:
    yield from scan_images(source_dir, **kwargs)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        rel = path.resolve().relative_to(parent.resolve())
        return rel != Path(".")
    except ValueError:
        return False
