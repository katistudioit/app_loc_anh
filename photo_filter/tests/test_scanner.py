from pathlib import Path

from photo_filter.services.scanner import scan_images


def test_scan_images_filters_extensions_and_excludes_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = source / "output"
    source.mkdir()
    destination.mkdir()
    (source / "a.JPG").write_bytes(b"x")
    (source / "b.txt").write_text("x")
    (destination / "old.png").write_bytes(b"x")
    (source / "nested").mkdir()
    (source / "nested" / "c.png").write_bytes(b"x")

    result = scan_images(source, recursive=True, exclude_dir=destination)

    assert [path.name for path in result] == ["a.JPG", "c.png"]


def test_scan_images_supports_cr3_and_tuple_extension(tmp_path: Path) -> None:
    source = tmp_path / "raw_source"
    source.mkdir()
    (source / "photo_01.CR3").write_bytes(b"canon_raw_data")
    (source / "photo_02.cr2").write_bytes(b"canon_cr2_data")
    (source / "photo_03.jpg").write_bytes(b"jpeg_data")
    (source / "notes.doc").write_text("doc")

    # Scan with canon raw tuple
    canon_raws = scan_images(source, extension=(".cr3", ".cr2"))
    assert [path.name for path in canon_raws] == ["photo_01.CR3", "photo_02.cr2"]

    # Scan all images
    all_images = scan_images(source)
    assert [path.name for path in all_images] == ["photo_01.CR3", "photo_02.cr2", "photo_03.jpg"]


def test_scan_images_when_destination_is_parent_folder(tmp_path: Path) -> None:
    # Reproduce studio workflow: Destination is the parent directory of source folder
    # e.g., source = D:\2026\04.09\100MSDCF, destination = D:\2026\04.09
    parent_dest = tmp_path / "customer_job"
    parent_dest.mkdir()
    camera_card_source = parent_dest / "100MSDCF"
    camera_card_source.mkdir()

    (camera_card_source / "A7500212.ARW").write_bytes(b"arw_data")
    (camera_card_source / "A7500212.JPG").write_bytes(b"jpg_data")
    (camera_card_source / "A7500117.ARW").write_bytes(b"arw_data_2")

    # Scanning camera_card_source with exclude_dir=parent_dest must NOT exclude files inside camera_card_source!
    scanned = scan_images(camera_card_source, exclude_dir=parent_dest)
    assert len(scanned) == 3
    assert {p.name for p in scanned} == {"A7500212.ARW", "A7500212.JPG", "A7500117.ARW"}


