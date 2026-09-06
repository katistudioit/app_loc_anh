from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from photo_filter.services.security import (
    start_security_watchdog,
    verify_security_environment,
)
from photo_filter.ui.main_window import MainWindow


def main() -> int:
    if not verify_security_environment():
        sys.exit(0)

    start_security_watchdog()

    app = QApplication(sys.argv)
    app.setApplicationName("KATISTUDIO")
    app.setApplicationDisplayName("KATISTUDIO LỌC ẢNH")
    app.setOrganizationName("KATISTUDIO")

    base_dir = Path(__file__).resolve().parent
    qss_candidates = [
        base_dir / "ui" / "styles.qss",
        base_dir / "styles.qss",
        Path.cwd() / "photo_filter" / "ui" / "styles.qss",
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        qss_candidates.insert(0, meipass / "photo_filter" / "ui" / "styles.qss")
        qss_candidates.insert(0, meipass / "ui" / "styles.qss")

    for stylesheet in qss_candidates:
        if stylesheet.exists():
            content = stylesheet.read_text(encoding="utf-8")
            from photo_filter.ui.main_window import resolve_asset
            chevron = str(resolve_asset("chevron_down.svg")).replace("\\", "/")
            check = str(resolve_asset("check.svg")).replace("\\", "/")
            content = content.replace("ui/assets/chevron_down.svg", chevron)
            content = content.replace("ui/assets/check.svg", check)
            app.setStyleSheet(content)
            break

    from photo_filter.ui.main_window import resolve_asset
    ico_path = resolve_asset("app_logo.ico")
    if ico_path.exists():
        app.setWindowIcon(QIcon(str(ico_path)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
