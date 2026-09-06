from pathlib import Path
from photo_filter.models.transfer_item import TransferItem, TransferStatus
from photo_filter.services.matcher import match_files
from photo_filter.services.message_parser import parse_selection_message
from photo_filter.services.organizer import (
    execute_operations,
    generate_classification_content,
    plan_operations,
    write_classification_txt,
)

SAMPLE_BOSS_MESSAGE = """✨ CÓ KHÁCH CHỌN ẢNH
👤 KHÁCH HÀNG 📁 FOLDER GỐC 📊 TỔNG FILE
04.09 BABY ĐÃ GOM XONG VÀO DRIVE 7 ảnh
──────────────────────────────────────
⬇️ CHI TIẾT DANH SÁCH CHỌN ⬇️
📁 THƯ MỤC GỐC – ❤️ ẢNH BÀN (5 ảnh)
A7500212 A7500223 A7500290 A7500261 A7500233

📁 THƯ MỤC GỐC – ⭐ ẢNH LỚN (2 ảnh)
A7500117 A7500265

KATI STUDIO • Hệ thống tự động • 21:18 04/09/2026"""


def test_parse_boss_notification_message() -> None:
    parsed = parse_selection_message(SAMPLE_BOSS_MESSAGE)
    assert parsed.is_structured is True
    assert parsed.customer_name == "04.09 BABY"
    assert len(parsed.groups) == 2

    group_ban = parsed.groups[0]
    assert group_ban.name == "ẢNH BÀN"
    assert group_ban.codes == ["A7500212", "A7500223", "A7500290", "A7500261", "A7500233"]

    group_lon = parsed.groups[1]
    assert group_lon.name == "ẢNH LỚN"
    assert group_lon.codes == ["A7500117", "A7500265"]

    assert len(parsed.all_codes) == 7


def test_match_files_with_boss_message() -> None:
    parsed = parse_selection_message(SAMPLE_BOSS_MESSAGE)

    files = [
        Path("A7500212.ARW"),
        Path("A7500223.JPG"),
        Path("A7500290.CR3"),
        Path("A7500261.DNG"),
        Path("A7500233.JPG"),
        Path("A7500117.JPG"),
        Path("A7500265.ARW"),
        Path("A7500999.JPG"),  # Not selected
    ]

    matched_items = match_files(files, parsed, match_mode="last_4_digits")
    assert len(matched_items) == 7

    items_ban = [it for it in matched_items if it.category == "ẢNH BÀN"]
    assert len(items_ban) == 5
    assert {it.source.name for it in items_ban} == {
        "A7500212.ARW", "A7500223.JPG", "A7500290.CR3", "A7500261.DNG", "A7500233.JPG"
    }

    items_lon = [it for it in matched_items if it.category == "ẢNH LỚN"]
    assert len(items_lon) == 2
    assert {it.source.name for it in items_lon} == {"A7500117.JPG", "A7500265.ARW"}


def test_plan_and_execute_category_subfolders(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    dst_dir = tmp_path / "output"

    # Create dummy files
    f1 = src_dir / "A7500212.JPG"
    f2 = src_dir / "A7500117.JPG"
    f1.write_bytes(b"photo1")
    f2.write_bytes(b"photo2")

    items = [
        TransferItem(source=f1, matched_code="A7500212", category="ẢNH BÀN"),
        TransferItem(source=f2, matched_code="A7500117", category="ẢNH LỚN"),
    ]

    planned = plan_operations(
        items,
        dst_dir,
        "copy",
        create_category_subfolders=True,
        use_single_raw_folder=False,
        customer_folder="04.09 BABY",
    )

    assert planned[0].destination == dst_dir / "04.09 BABY" / "ẢNH BÀN" / "A7500212.JPG"
    assert planned[1].destination == dst_dir / "04.09 BABY" / "ẢNH LỚN" / "A7500117.JPG"

    executed = execute_operations(planned, "copy")
    assert all(it.status == TransferStatus.COPIED for it in executed)

    # Verify files created in subfolders
    assert (dst_dir / "04.09 BABY" / "ẢNH BÀN" / "A7500212.JPG").exists()
    assert (dst_dir / "04.09 BABY" / "ẢNH LỚN" / "A7500117.JPG").exists()
    assert (dst_dir / "04.09 BABY" / "ẢNH BÀN" / "A7500212.JPG").read_bytes() == b"photo1"


def test_plan_and_execute_single_raw_folder_and_classification_txt(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    dst_dir = tmp_path / "output"

    f1 = src_dir / "A7500212.ARW"
    f2 = src_dir / "A7500117.CR3"
    f1.write_bytes(b"arw_raw_data")
    f2.write_bytes(b"cr3_raw_data")

    # Photo 1 is both ẢNH BÀN and ẢNH LỚN, photo 2 is ẢNH LỚN
    items = [
        TransferItem(source=f1, matched_code="A7500212", category="ẢNH BÀN"),
        TransferItem(source=f1, matched_code="A7500212", category="ẢNH LỚN"),
        TransferItem(source=f2, matched_code="A7500117", category="ẢNH LỚN"),
    ]

    planned = plan_operations(
        items,
        dst_dir,
        "copy",
        use_single_raw_folder=True,
        raw_folder_name="raw chọn",
        customer_folder="04.09 BABY",
    )

    # All files go into the single 'raw chọn' folder
    raw_folder = dst_dir / "04.09 BABY" / "raw chọn"
    assert planned[0].destination == raw_folder / "A7500212.ARW"
    # Duplicate selection of the same source file points to the same destination without _001 collision
    assert planned[1].destination == raw_folder / "A7500212.ARW"
    assert planned[2].destination == raw_folder / "A7500117.CR3"

    executed = execute_operations(planned, "copy")
    assert all(it.status == TransferStatus.COPIED for it in executed)

    # Both files exist in raw chọn
    assert (raw_folder / "A7500212.ARW").exists()
    assert (raw_folder / "A7500117.CR3").exists()

    # Write classification TXT
    txt_path = write_classification_txt(
        raw_folder,
        executed,
        customer_name="04.09 BABY",
        folder_name="raw chọn",
    )
    assert txt_path.exists()
    txt_content = txt_path.read_text(encoding="utf-8")

    assert "KATI STUDIO - DANH SÁCH ẢNH CHỌN" in txt_content
    assert "04.09 BABY" in txt_content
    assert "raw chọn" in txt_content
    assert "[ẢNH BÀN]" in txt_content
    assert "[ẢNH LỚN]" in txt_content
    assert "A7500212.ARW" in txt_content
    assert "A7500117.CR3" in txt_content


def test_filter_worker_boss_message_single_folder_and_txt(tmp_path: Path) -> None:
    from photo_filter.services.worker import FilterWorker

    src_dir = tmp_path / "source_photos"
    dst_dir = tmp_path / "output_photos"
    src_dir.mkdir()
    dst_dir.mkdir()

    # Create matching RAW files in source
    (src_dir / "A7500212.ARW").write_bytes(b"raw1")
    (src_dir / "A7500117.CR3").write_bytes(b"raw2")
    (src_dir / "OTHER_9999.JPG").write_bytes(b"other")

    # Step 1: Preview mode with worker
    preview_worker = FilterWorker(
        source_dir=src_dir,
        destination_dir=dst_dir,
        codes_text=SAMPLE_BOSS_MESSAGE,
        operation="copy",
        extension=None,
        recursive=True,
        match_mode="last_4_digits",
        create_category_subfolders=False,
        use_single_raw_folder=True,
        raw_folder_name="raw chọn",
        create_txt_classification=True,
        customer_folder="04.09 BABY",
        execute=False,
    )

    preview_items = []
    preview_worker.preview_ready.connect(lambda items, scanned, codes: preview_items.extend(items))
    preview_worker.run()

    assert len(preview_items) == 2
    raw_target_folder = dst_dir / "04.09 BABY" / "raw chọn"
    assert preview_items[0].destination == raw_target_folder / "A7500212.ARW"
    assert preview_items[1].destination == raw_target_folder / "A7500117.CR3"

    # Step 2: Execution mode with worker
    exec_worker = FilterWorker(
        source_dir=src_dir,
        destination_dir=dst_dir,
        codes_text=SAMPLE_BOSS_MESSAGE,
        operation="copy",
        extension=None,
        recursive=True,
        match_mode="last_4_digits",
        create_category_subfolders=False,
        use_single_raw_folder=True,
        raw_folder_name="raw chọn",
        create_txt_classification=True,
        customer_folder="04.09 BABY",
        execute=True,
        items=preview_items,
    )

    executed_items = []
    exec_worker.finished.connect(lambda items: executed_items.extend(items))
    exec_worker.run()

    assert len(executed_items) == 2
    assert all(it.status == TransferStatus.COPIED for it in executed_items)

    # Check files exist in raw chọn
    assert (raw_target_folder / "A7500212.ARW").exists()
    assert (raw_target_folder / "A7500117.CR3").exists()

    # Check danh_sach_chon_anh.txt exists in both raw chọn and customer folder
    txt_in_raw = raw_target_folder / "danh_sach_chon_anh.txt"
    txt_in_cust = dst_dir / "04.09 BABY" / "danh_sach_chon_anh.txt"

    assert txt_in_raw.exists()
    assert txt_in_cust.exists()

    content = txt_in_raw.read_text(encoding="utf-8")
    assert "04.09 BABY" in content
    assert "[ẢNH BÀN]" in content
    assert "[ẢNH LỚN]" in content
    assert "A7500212.ARW" in content
    assert "A7500117.CR3" in content
