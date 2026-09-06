from pathlib import Path

from photo_filter.models.transfer_item import TransferStatus
from photo_filter.services.organizer import execute_operations, plan_operations, safe_filename
from photo_filter.services.matcher import match_files


def test_copy_does_not_remove_source_and_avoids_collision(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    image = source / "IMG_001.jpg"
    image.write_bytes(b"image")
    (destination / image.name).write_bytes(b"existing")

    items = plan_operations(match_files([image], ["IMG_001"]), destination, "copy")
    result = execute_operations(items, "copy")

    assert result[0].status == TransferStatus.COPIED
    assert image.exists()
    assert result[0].destination == destination / "IMG_001_001.jpg"
    assert result[0].destination.read_bytes() == b"image"


def test_rename_sanitizes_filename(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    image = source / "original.png"
    image.write_bytes(b"image")

    items = plan_operations(match_files([image], ["original"]), destination, "rename")
    result = execute_operations(items, "rename")

    assert result[0].status == TransferStatus.RENAMED
    assert (destination / "original.png").exists()
    assert not image.exists()
    assert safe_filename("A:B") == "A_B"
    assert safe_filename("CON") == "_CON"
