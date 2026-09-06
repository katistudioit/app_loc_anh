from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from photo_filter.models.transfer_item import TransferItem


def export_report(
    items: Iterable[TransferItem],
    report_dir: Path,
    *,
    source_dir: Path,
    destination_dir: Path,
    operation: str,
) -> tuple[Path, Path]:
    report_dir = report_dir.expanduser().resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = [item.as_dict() for item in items]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = report_dir / f"shotpik_report_{stamp}"
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(source_dir),
        "destination_dir": str(destination_dir),
        "operation": operation,
        "items": rows,
    }

    json_path = stem.with_suffix(".json")
    csv_path = stem.with_suffix(".csv")
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "matched_code", "category", "destination", "status", "error"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return csv_path, json_path
