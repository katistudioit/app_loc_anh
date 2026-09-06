from pathlib import Path

project = Path(SPECPATH)

analysis = Analysis(
    [str(project / "app.py")],
    pathex=[str(project.parent)],
    binaries=[],
    datas=[
        (str(project / "ui" / "styles.qss"), "ui"),
        (str(project / "ui" / "assets"), "ui/assets"),
        (str(project / "ui" / "styles.qss"), "photo_filter/ui"),
        (str(project / "ui" / "assets"), "photo_filter/ui/assets"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "imagehash",
        "PIL",
        "PIL.Image",
        "rawpy",
        "scipy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="KATISTUDIO",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project / "ui" / "assets" / "app_logo.ico"),
)
