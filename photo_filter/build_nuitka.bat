@echo off
chcp 65001 >nul
echo =======================================================
echo   KATISTUDIO - BIÊN DỊCH NATIVE NUITKA (ANTI-CRACK)
echo =======================================================
echo.

cd /d "%~dp0"
call .venv\Scripts\activate.bat

echo [1/3] Kiểm tra công cụ biên dịch MSVC...
python -m nuitka --version

echo.
echo [2/3] Bắt đầu biên dịch toàn bộ mã nguồn sang mã máy C/C++...
python -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyside6 ^
  --windows-disable-console ^
  --windows-icon-from-ico=ui\assets\app_logo.ico ^
  --windows-company-name=KATISTUDIO ^
  --windows-product-name="KATISTUDIO LỌC ẢNH" ^
  --windows-file-version=1.0.0.0 ^
  --windows-product-version=1.0.0.0 ^
  --windows-file-description="KATISTUDIO LỌC ẢNH" ^
  --include-package=photo_filter ^
  --include-data-dir="ui=photo_filter/ui" ^
  --include-data-dir="ui=ui" ^
  --output-dir="..\dist" ^
  --output-filename=KATISTUDIO.exe ^
  --assume-yes-for-downloads ^
  app.py

echo.
echo [3/3] Dọn dẹp cache trung gian...
if exist "..\dist\app.dist" rd /s /q "..\dist\app.dist"
if exist "..\dist\app.build" rd /s /q "..\dist\app.build"
if exist "..\dist\app.onefile-build" rd /s /q "..\dist\app.onefile-build"

echo.
echo =======================================================
echo   HOÀN TẤT! File thực thi bảo vệ tại: dist\KATISTUDIO.exe
echo =======================================================
pause
