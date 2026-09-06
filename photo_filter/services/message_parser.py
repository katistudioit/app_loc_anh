from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Common studio categories in Vietnamese photography studios
KNOWN_STUDIO_CATEGORIES = (
    "ẢNH BÀN",
    "ẢNH LỚN",
    "ẢNH CỔNG",
    "ẢNH PHÓNG",
    "ẢNH ĐỂ BÀN",
    "ẢNH TREO TƯỜNG",
    "ALBUM",
    "ẢNH ALBUM",
    "ẢNH BÌA",
    "RETOUCH",
    "CHỈNH SỬA",
    "ẢNH RỬA",
    "ẢNH ÉP GỖ",
    "ẢNH TRÁNG GƯƠNG",
    "ẢNH PHA LÊ",
    "SLIDE",
    "ẢNH CHỌN",
    "THƯ MỤC GỐC",
)

VIETNAMESE_ACCENTS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)


@dataclass
class ParsedSelectionGroup:
    name: str
    codes: list[str] = field(default_factory=list)
    raw_header: str = ""
    declared_count: int | None = None


@dataclass
class ParsedSelectionMessage:
    raw_text: str = ""
    customer_name: str = ""
    folder_info: str = ""
    declared_total: int | None = None
    groups: list[ParsedSelectionGroup] = field(default_factory=list)
    is_structured: bool = False

    @property
    def all_codes(self) -> list[str]:
        """Flattened list of all unique codes across all groups."""
        seen = set()
        res = []
        for g in self.groups:
            for c in g.codes:
                k = c.casefold()
                if k not in seen:
                    seen.add(k)
                    res.append(c)
        return res

    @property
    def total_codes_count(self) -> int:
        return sum(len(g.codes) for g in self.groups)

    def summary_text(self) -> str:
        if not self.is_structured or not self.groups:
            return f"Danh sách {len(self.all_codes)} mã ảnh"
        parts = []
        if self.customer_name:
            parts.append(f"Khách: {self.customer_name}")
        group_descs = [f"{g.name}: {len(g.codes)} ảnh" for g in self.groups]
        parts.append(", ".join(group_descs))
        return " • ".join(parts)


def clean_group_name(header: str) -> str:
    """Extract clean category name from messy headers like '📁 THƯ MỤC GỐC – ❤️ ẢNH BÀN (5 ảnh)'."""
    s = header.strip()
    # Remove leading icons/bullets
    s = re.sub(r"^[📁📂🗂️🗂\[\*\•\-\–\—\s]+", "", s)
    # Remove 'THƯ MỤC GỐC' prefix if followed by separator and category
    s = re.sub(
        r"^(?:THƯ\s*MỤC\s*GỐC|THƯ\s*MỤC|NHÓM|DANH\s*MỤC)\s*[\-–—:]*\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Remove emoji decor (hearts, stars, cameras, etc.)
    s = re.sub(r"^[❤️⭐🌟📸🎉✨🔹🔸💙💜💚💛🤍🖤💖\s]+", "", s)
    # Remove trailing count like '(5 ảnh)', '(2 file)'
    s = re.sub(
        r"[\(\[]\s*\d+\s*(?:ảnh|file|tấm|hình)?\s*[\)\]]",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Remove trailing punctuation
    s = s.strip(" -–—:[]()")
    return s.strip() or "Nhóm ảnh"


def extract_declared_count(header: str) -> int | None:
    m = re.search(r"[\(\[]\s*(\d+)\s*(?:ảnh|file|tấm|hình)?\s*[\)\]]", header, re.IGNORECASE)
    return int(m.group(1)) if m else None


def is_group_header_line(line: str) -> bool:
    line_clean = line.strip()
    if not line_clean:
        return False

    # Ignore common message titles/footers
    upper = line_clean.upper()
    if any(k in upper for k in ["CHI TIẾT DANH SÁCH", "CÓ KHÁCH CHỌN", "KATI STUDIO", "HỆ THỐNG TỰ ĐỘNG", "TỔNG FILE"]):
        return False

    # 1. Bracket format: [ẢNH BÀN] or [ALBUM]
    if line_clean.startswith("[") and line_clean.endswith("]"):
        content = line_clean[1:-1].strip()
        if not is_valid_photo_code(content):
            return True

    # 2. Header with folder emoji + category or count
    has_folder_icon = bool(re.search(r"[📁📂🗂]", line_clean))
    has_known_cat = any(cat in upper for cat in KNOWN_STUDIO_CATEGORIES)
    has_count = bool(re.search(r"\(\s*\d+\s*(?:ảnh|file|tấm|hình)?\s*\)", line_clean, re.IGNORECASE))

    if has_folder_icon and (has_known_cat or has_count):
        return True

    if has_known_cat and (has_count or line_clean.endswith(":") or "–" in line_clean or "-" in line_clean):
        return True

    # 3. Check for pattern 'CATEGORY: code code...'
    if ":" in line_clean:
        prefix = line_clean.split(":", 1)[0].strip()
        if any(cat in prefix.upper() for cat in KNOWN_STUDIO_CATEGORIES):
            return True

    return False


def is_valid_photo_code(token: str) -> bool:
    """Check if token is a valid camera photo code (e.g. A7500212, IMG_1234, 0212, DSC_0042)."""
    t = token.strip().strip(",;:\"'()[]")
    if not t:
        return False

    # Camera filenames never have accented Vietnamese letters
    if VIETNAMESE_ACCENTS.search(t):
        return False

    # Ignore pure words or dates/times
    if "/" in t or ":" in t:
        return False

    # Ignore common studio non-code words
    upper = t.upper()
    if upper in {
        "KATI", "STUDIO", "DRIVE", "FILE", "FOLDER", "PHOTO", "FILTER",
        "DATE", "TOTAL", "SELECT", "THUMUC", "GOC", "ANH", "BAN", "LON",
        "BABY", "CUOI", "WEDDING", "PREVIEW", "XONG", "GOM", "DISCORD",
        "HETHONG", "DANHSACH", "SYSTEM", "BOT", "CHANNEL",
    }:
        return False

    # Valid code: alphanumeric with digits, between 2 and 40 characters
    if not (2 <= len(t) <= 40):
        return False

    # Must contain at least one digit or be a known photo stem format (like _MG_, IMG_, DSC)
    has_digit = any(c.isdigit() for c in t)
    looks_like_file = bool(re.match(r"^[A-Za-z0-9_\-\.]{2,40}$", t))

    return looks_like_file and has_digit


def parse_customer_name(text: str) -> str:
    """Extract customer name from boss notification text."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        line_str = line.strip()
        # Direct format: '👤 KHÁCH HÀNG: 04.09 BABY' or 'KHÁCH HÀNG: 04.09 BABY'
        m = re.search(
            r"(?:👤\s*KHÁCH\s*HÀNG|KHÁCH\s*HÀNG)[:\s]+([^\s📁📊\t\n]+(?: [^\s📁📊\t\n]+)*)",
            line_str,
            re.IGNORECASE,
        )
        if m:
            val = m.group(1).strip()
            # Clean trailing labels if they were on same line
            val = re.split(r"[\t\s]{2,}|📁|📊|FOLDER|TỔNG", val, flags=re.IGNORECASE)[0].strip()
            if val and "ĐÃ GOM" not in val.upper():
                return val

        # Grid / tabular format where 'KHÁCH HÀNG' is on line i and value on line i+1
        if "KHÁCH HÀNG" in line_str.upper() and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            m2 = re.search(
                r"^(.*?)(?:\s+(?:ĐÃ\s+GOM|VÀO\s+DRIVE|DRIVE|\d+\s*ảnh)|\s{2,}|\t|📁|📊)",
                next_line,
                re.IGNORECASE,
            )
            if m2 and m2.group(1).strip():
                cand = m2.group(1).strip()
                if "CHI TIẾT" not in cand.upper() and "THƯ MỤC" not in cand.upper():
                    return cand

    return ""


def parse_selection_message(raw_text: str) -> ParsedSelectionMessage:
    """
    Parse pasted selection text into structured groups with photo codes.
    Handles:
    - Boss bot messages with groups (📁 THƯ MỤC GỐC – ❤️ ẢNH BÀN, ẢNH LỚN...)
    - Simple grouped codes ([ẢNH BÀN] \n A7500212...)
    - Plain lists of codes separated by spaces, commas, or newlines.
    """
    cleaned_text = raw_text.strip()
    if not cleaned_text:
        return ParsedSelectionMessage()

    customer = parse_customer_name(cleaned_text)

    # Check declared total if present
    total_m = re.search(r"(\d+)\s*(?:ảnh|file|tấm|hình)", cleaned_text, re.IGNORECASE)
    declared_total = int(total_m.group(1)) if total_m else None

    lines = cleaned_text.splitlines()

    # Determine if text has group headers
    has_groups = any(is_group_header_line(l) for l in lines)

    if not has_groups:
        # Standard plain list of codes
        codes = []
        seen = set()
        # Split on whitespace, commas, semicolons
        tokens = re.split(r"[\s,;\t\n]+", cleaned_text)
        for tok in tokens:
            cleaned_tok = tok.strip().strip(",;:\"'()[]")
            if is_valid_photo_code(cleaned_tok):
                k = cleaned_tok.casefold()
                if k not in seen:
                    seen.add(k)
                    codes.append(cleaned_tok)

        default_group = ParsedSelectionGroup(name="", codes=codes)
        return ParsedSelectionMessage(
            raw_text=raw_text,
            customer_name=customer,
            declared_total=declared_total,
            groups=[default_group] if codes else [],
            is_structured=False,
        )

    # Structured parsing with groups
    groups: list[ParsedSelectionGroup] = []
    current_group: ParsedSelectionGroup | None = None

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        if is_group_header_line(line_str):
            # Check if line also has inline codes after colon, e.g. "ẢNH BÀN: A7500212 A7500223"
            inline_codes = []
            if ":" in line_str and not line_str.endswith(":"):
                header_part, codes_part = line_str.split(":", 1)
                gname = clean_group_name(header_part)
                tokens = re.split(r"[\s,;\t]+", codes_part.strip())
                inline_codes = [t.strip().strip(",;:\"'()[]") for t in tokens if is_valid_photo_code(t)]
            else:
                gname = clean_group_name(line_str)

            declared_cnt = extract_declared_count(line_str)
            current_group = ParsedSelectionGroup(
                name=gname,
                raw_header=line_str,
                declared_count=declared_cnt,
                codes=inline_codes,
            )
            groups.append(current_group)
            continue

        # Check for message footer or end markers
        upper = line_str.upper()
        if "KATI STUDIO" in upper and ("HỆ THỐNG" in upper or "TỰ ĐỘNG" in upper):
            current_group = None
            continue

        if current_group is not None:
            tokens = re.split(r"[\s,;\t]+", line_str)
            for tok in tokens:
                cleaned_tok = tok.strip().strip(",;:\"'()[]")
                if is_valid_photo_code(cleaned_tok):
                    if cleaned_tok not in current_group.codes:
                        current_group.codes.append(cleaned_tok)

    # Filter out empty groups if any
    non_empty_groups = [g for g in groups if g.codes]

    return ParsedSelectionMessage(
        raw_text=raw_text,
        customer_name=customer,
        declared_total=declared_total,
        groups=non_empty_groups,
        is_structured=len(non_empty_groups) > 0,
    )
