from pathlib import Path

from photo_filter.services.matcher import match_files, normalize_codes


def test_normalize_codes_preserves_order_and_removes_duplicates() -> None:
    assert normalize_codes(" IMG_001\nIMG_001, IMG_002\n") == ["IMG_001", "IMG_002"]


def test_match_files_is_case_insensitive_and_prefers_longest_code() -> None:
    files = [Path("IMG_001_backup.JPG"), Path("other.png")]
    items = match_files(files, ["001", "IMG_001"])
    assert len(items) == 1
    assert items[0].matched_code == "IMG_001"


def test_extension_in_code_matches_full_name() -> None:
    items = match_files([Path("DSC_1234.CR2"), Path("DSC_1234.jpg")], ["DSC_1234.CR2"])
    assert [item.source.name for item in items] == ["DSC_1234.CR2"]


def test_match_last_4_digits_camera_formats() -> None:
    files = [
        Path("_MG_1234.CR3"),    # Canon EOS R5/R6 CR3
        Path("IMG_0567.JPG"),    # Canon JPG
        Path("DSC_8901.ARW"),    # Sony Alpha RAW
        Path("20240907_9999.CR2"), # Canon CR2 with date prefix
        Path("IMG_12345.JPG"),   # Different 5-digit number (ends with 2345, NOT 1234)
        Path("DSC_0042.NEF"),    # Nikon RAW with leading zeroes
    ]

    # Test matching '1234' -> should match _MG_1234.CR3, but NOT IMG_12345.JPG
    items_1234 = match_files(files, ["1234"], match_mode="last_4_digits")
    assert [item.source.name for item in items_1234] == ["_MG_1234.CR3"]

    # Test matching '42' -> should match DSC_0042.NEF
    items_42 = match_files(files, ["42"], match_mode="last_4_digits")
    assert [item.source.name for item in items_42] == ["DSC_0042.NEF"]

    # Test matching multiple 4-digit codes
    items_multi = match_files(files, ["1234", "0567", "8901", "9999"], match_mode="last_4_digits")
    assert [item.source.name for item in items_multi] == [
        "_MG_1234.CR3",
        "IMG_0567.JPG",
        "DSC_8901.ARW",
        "20240907_9999.CR2",
    ]


def test_match_trailing_digits_and_prefix_modes() -> None:
    files = [Path("KATI_001.JPG"), Path("KATI_002_edit.PNG"), Path("OTHER_001.JPG")]

    # Starts with mode
    items_starts = match_files(files, ["KATI_"], match_mode="starts_with")
    assert len(items_starts) == 2

    # Ends with mode
    items_ends = match_files(files, ["_edit"], match_mode="ends_with")
    assert [item.source.name for item in items_ends] == ["KATI_002_edit.PNG"]

