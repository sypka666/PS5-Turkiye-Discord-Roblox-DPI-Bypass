@echo off
chcp 65001 >nul
echo [Build] PS5-DPI-Bypass.exe derleniyor...
if exist ".venv\Scripts\pyinstaller.exe" (
    .venv\Scripts\pyinstaller.exe --noconsole --onefile --clean --icon="app_icon.ico" --add-data "app_icon.ico;." --name "PS5-DPI-Bypass" ps5_dpi_proxy.py
) else (
    pyinstaller --noconsole --onefile --clean --icon="app_icon.ico" --add-data "app_icon.ico;." --name "PS5-DPI-Bypass" ps5_dpi_proxy.py
)
if exist "dist\PS5-DPI-Bypass.exe" (
    copy /Y "dist\PS5-DPI-Bypass.exe" "PS5-DPI-Bypass.exe" >nul
    echo [Basarili] PS5-DPI-Bypass.exe olusturuldu!
)
pause
