from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from photo_filter.models.transfer_item import TransferItem
from photo_filter.services.matcher import match_files, normalize_codes
from photo_filter.services.message_parser import parse_selection_message
from photo_filter.services.organizer import (
    execute_operations,
    plan_operations,
    safe_folder_name,
    write_classification_txt,
)
from photo_filter.services.scanner import scan_images


class FilterWorker(QObject):
    preview_ready = Signal(object, int, int)
    item_progress = Signal(int, int, object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        source_dir: Path,
        destination_dir: Path,
        codes_text: str,
        operation: str,
        extension: str | tuple[str, ...] | None,
        recursive: bool,
        contains: bool = True,
        match_mode: str | None = None,
        create_category_subfolders: bool = False,
        use_single_raw_folder: bool = True,
        raw_folder_name: str = "raw chọn",
        create_txt_classification: bool = True,
        customer_folder: str = "",
        *,
        execute: bool = False,
        items: list[TransferItem] | None = None,
        cancel_event: Event | None = None,
    ) -> None:
        super().__init__()
        self.source_dir = source_dir
        self.destination_dir = destination_dir
        self.codes_text = codes_text
        self.operation = operation
        self.extension = extension
        self.recursive = recursive
        self.match_mode = match_mode if match_mode is not None else contains
        self.create_category_subfolders = create_category_subfolders
        self.use_single_raw_folder = use_single_raw_folder
        self.raw_folder_name = raw_folder_name
        self.create_txt_classification = create_txt_classification
        self.customer_folder = customer_folder
        self.execute = execute
        self.items = items
        self.cancel_event = cancel_event or Event()

    @Slot()
    def run(self) -> None:
        try:
            if self.execute:
                result = execute_operations(
                    self.items or [],
                    self.operation,
                    progress=self._progress,
                    is_cancelled=self.cancel_event.is_set,
                )

                # Write classification TXT file if requested
                if self.create_txt_classification and result:
                    target_txt_dir = self.destination_dir.expanduser().resolve()
                    if self.customer_folder and self.customer_folder.strip():
                        target_txt_dir = target_txt_dir / safe_folder_name(self.customer_folder.strip())
                    if self.use_single_raw_folder:
                        raw_name = self.raw_folder_name.strip() if self.raw_folder_name and self.raw_folder_name.strip() else "raw chọn"
                        raw_dir = target_txt_dir / safe_folder_name(raw_name)
                        # Save inside 'raw chọn'
                        write_classification_txt(
                            raw_dir,
                            result,
                            customer_name=self.customer_folder,
                            folder_name=raw_name,
                        )
                        # Also save a copy in parent customer folder for easy access
                        if self.customer_folder and self.customer_folder.strip():
                            write_classification_txt(
                                target_txt_dir,
                                result,
                                customer_name=self.customer_folder,
                                folder_name=raw_name,
                            )
                    else:
                        write_classification_txt(
                            target_txt_dir,
                            result,
                            customer_name=self.customer_folder,
                            folder_name="",
                        )

                self.finished.emit(result)
                return

            parsed = parse_selection_message(self.codes_text)
            codes = parsed.all_codes or normalize_codes(self.codes_text)

            files = scan_images(
                self.source_dir,
                recursive=self.recursive,
                extension=self.extension,
                exclude_dir=self.destination_dir,
            )

            # Match files with group categories if structured, or flat list
            items = match_files(
                files,
                parsed if parsed.is_structured else codes,
                match_mode=self.match_mode,
            )

            # Plan operations with single 'raw chọn' or category subfolders
            planned = plan_operations(
                items,
                self.destination_dir,
                self.operation,
                create_category_subfolders=self.create_category_subfolders,
                use_single_raw_folder=self.use_single_raw_folder,
                raw_folder_name=self.raw_folder_name,
                customer_folder=self.customer_folder,
            )
            self.preview_ready.emit(planned, len(files), len(codes))
        except (OSError, ValueError, NotADirectoryError) as error:
            self.failed.emit(str(error))

    def _progress(self, current: int, total: int, item: TransferItem) -> None:
        self.item_progress.emit(current, total, item)


__all__ = ["FilterWorker"]
