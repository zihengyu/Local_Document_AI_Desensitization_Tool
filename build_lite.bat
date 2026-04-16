@echo off
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /f /q chat_desensitizer_lite.spec 2>nul

python -c "import PyQt5" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 当前 Python 环境未安装 PyQt5。
  echo [HINT] 请先执行: python -m pip install PyQt5
  exit /b 1
)

echo Building chat_desensitizer_lite...
python -m PyInstaller --noconfirm --windowed --name chat_desensitizer_lite ^
  --add-data "config;config" ^
  --hidden-import Data_Masking.chat_desensitizer_lite ^
  --hidden-import Data_Masking.chat_parser ^
  --collect-all PyQt5 ^
  Data_Masking\ui\chat_gui_app.py
