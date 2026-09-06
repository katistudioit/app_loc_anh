from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from photo_filter.models.transfer_item import TransferItem
from photo_filter.services.message_parser import (
    ParsedSelectionGroup,
    ParsedSelectionMessage,
    parse_selection_message,
)

# Supported match modes
MODE_LAST_4_DIGITS = "last_4_digits"      # 4 số cuối tên file (Ví dụ: 1234 -> IMG_1234, _MG_1234, A7500212 -> DSC00212)
MODE_TRAILING_DIGITS = "trailing_digits"  # Số cuối file linh hoạt (Ví dụ: 42 -> IMG_0042)
MODE_CONTAINS = "contains"                # Chuỗi con trong tên
MODE_EXACT = "exact"                      # Tên chính xác
MODE_STARTS_WITH = "starts_with"          # Bắt đầu bằng mã
MODE_ENDS_WITH = "ends_with"              # Kết thúc bằng mã


def extract_trailing_digits(text: str) -> str | None:
    """Extract trailing sequence of digits from text, e.g. 'IMG_1234' -> '1234'."""
    match = re.search(r"(\d+)(?:\D*)$", text)
    return match.group(1) if match else None


def extract_all_digits(text: str) -> str:
    """Extract all digits in string as a concatenated string."""
    return "".join(re.findall(r"\d", text))


def normalize_codes(raw_text: str) -> list[str]:
    """
    Normalize image codes from raw text while preserving order and uniqueness.
    Supports boss bot messages, Excel/Sheets copy-paste, spaces, tabs, commas, newlines.
    """
    cleaned = raw_text.strip()
    if not cleaned:
        return []

    parsed = parse_selection_message(cleaned)
    if parsed.is_structured and parsed.all_codes:
        return parsed.all_codes

    # Fallback to general tokenization
    tokens = re.split(r"[\s,;\t\n]+", cleaned)
    result: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        code = tok.strip().strip(",;:\"'()[]")
        if not code:
            continue
        key = code.casefold()
        if key not in seen:
            result.append(code)
            seen.add(key)
    return result


def match_files(
    files: Iterable[Path],
    codes: Iterable[str] | ParsedSelectionMessage,
    *,
    match_mode: str | bool = MODE_LAST_4_DIGITS,
    contains: bool | None = None,
) -> list[TransferItem]:
    """
    Match files against codes.
    If codes is a ParsedSelectionMessage with multiple groups (e.g. ẢNH BÀN, ẢNH LỚN),
    it generates TransferItems tagged with their respective category.
    """
    resolved_mode = _resolve_mode(match_mode, contains)
    file_list = list(files)

    if isinstance(codes, ParsedSelectionMessage) and codes.is_structured:
        return _match_grouped_files(file_list, codes, resolved_mode)

    # Standard / flat matching
    if isinstance(codes, ParsedSelectionMessage):
        raw_codes = codes.all_codes
    elif isinstance(codes, str):
        parsed = parse_selection_message(codes)
        if parsed.is_structured:
            return _match_grouped_files(file_list, parsed, resolved_mode)
        raw_codes = parsed.all_codes or normalize_codes(codes)
    else:
        raw_codes = normalize_codes("\n".join(codes))

    ordered_codes = sorted(raw_codes, key=lambda code: (-len(code), code.casefold()))
    items: list[TransferItem] = []

    for path in file_list:
        filename = path.name.casefold()
        stem = path.stem.casefold()
        matches = [code for code in ordered_codes if _matches_item(code, filename, stem, resolved_mode)]
        if matches:
            items.append(TransferItem(source=path, matched_code=matches[0], category=""))

    return items


def _match_grouped_files(
    files: list[Path],
    message: ParsedSelectionMessage,
    resolved_mode: str,
) -> list[TransferItem]:
    """Match files per group so items carry their category name (ẢNH BÀN, ẢNH LỚN, etc.)."""
    items: list[TransferItem] = []

    for group in message.groups:
        ordered_codes = sorted(group.codes, key=lambda code: (-len(code), code.casefold()))
        for path in files:
            filename = path.name.casefold()
            stem = path.stem.casefold()
            matches = [code for code in ordered_codes if _matches_item(code, filename, stem, resolved_mode)]
            if matches:
                items.append(
                    TransferItem(
                        source=path,
                        matched_code=matches[0],
                        category=group.name,
                    )
                )

    return items


def _resolve_mode(match_mode: str | bool, contains: bool | None) -> str:
    """Resolve match mode string taking into account legacy boolean parameters."""
    if contains is not None:
        return MODE_CONTAINS if contains else MODE_EXACT
    if isinstance(match_mode, bool):
        return MODE_CONTAINS if match_mode else MODE_EXACT
    return str(match_mode).lower()


def _matches_item(code: str, filename: str, stem: str, mode: str) -> bool:
    candidate = code.casefold().strip()
    if not candidate:
        return False

    if mode == MODE_LAST_4_DIGITS:
        return _matches_last_4_digits(candidate, filename, stem)
    elif mode == MODE_TRAILING_DIGITS:
        return _matches_trailing_digits(candidate, filename, stem)
    elif mode == MODE_STARTS_WITH:
        return stem.startswith(candidate) or filename.startswith(candidate)
    elif mode == MODE_ENDS_WITH:
        return stem.endswith(candidate) or filename.endswith(candidate)
    elif mode == MODE_EXACT:
        target = filename if Path(candidate).suffix else stem
        return candidate == target
    else:  # default: MODE_CONTAINS
        target = filename if Path(candidate).suffix else stem
        return candidate in target


def _matches_last_4_digits(candidate: str, filename: str, stem: str) -> bool:
    # 1. Direct full match
    if candidate == stem or candidate == filename:
        return True

    # If candidate contains letters (like 'IMG_1234', 'A7500212'), allow substring if matched
    if not candidate.isdigit():
        if candidate in stem or candidate in filename:
            return True

    # 2. Extract digits from candidate
    cand_digits = extract_all_digits(candidate)
    if not cand_digits:
        return False

    stem_trailing = extract_trailing_digits(stem)
    stem_all = extract_all_digits(stem)

    # Candidate last 4 digits (e.g. 1234 -> 1234, A7500212 -> 0212)
    cand_last_4 = cand_digits[-4:] if len(cand_digits) >= 4 else cand_digits

    # Check against stem trailing digits
    if stem_trailing:
        if stem_trailing == cand_digits:
            return True
        stem_last_4 = stem_trailing[-4:] if len(stem_trailing) >= 4 else stem_trailing
        if len(cand_last_4) == 4 and stem_last_4 == cand_last_4:
            return True
        if len(cand_last_4) < 4:
            try:
                if int(stem_trailing) == int(cand_last_4):
                    return True
            except ValueError:
                pass
            if len(stem_trailing) >= 4 and stem_trailing[-4:] == cand_last_4.zfill(4):
                return True

    # Check against stem all digits
    if stem_all:
        if stem_all == cand_digits:
            return True
        stem_all_last_4 = stem_all[-4:] if len(stem_all) >= 4 else stem_all
        if len(cand_last_4) == 4 and stem_all_last_4 == cand_last_4:
            return True
        if len(cand_last_4) < 4:
            try:
                if int(stem_all[-4:]) == int(cand_last_4):
                    return True
            except (ValueError, IndexError):
                pass

    return False


def _matches_trailing_digits(candidate: str, filename: str, stem: str) -> bool:
    if not candidate.isdigit():
        if candidate in stem or candidate in filename:
            return True
        cand_digits = extract_trailing_digits(candidate)
        if not cand_digits:
            return False
    else:
        cand_digits = candidate

    trailing = extract_trailing_digits(stem)
    if not trailing:
        return False

    if trailing == cand_digits or trailing.endswith(cand_digits):
        return True

    try:
        if int(trailing) == int(cand_digits):
            return True
    except ValueError:
        pass

    return False
