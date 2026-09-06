import json
from pathlib import Path

from photo_filter.models.transfer_item import TransferItem, TransferStatus
from photo_filter.services.report import export_report


def test_export_report_writes_csv_and_json(tmp_path: Path) -> None:
    source = tmp_path / "a.jpg"
    item = TransferItem(source=source, matched_code="A", status=TransferStatus.COPIED)
    csv_path, json_path = export_report([item], tmp_path, source_dir=tmp_path, destination_dir=tmp_path, operation="copy")

    assert csv_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["items"][0]["matched_code"] == "A"
    assert "matched_code" in csv_path.read_text(encoding="utf-8-sig")
