@echo off
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /f /q chat_desensitizer_lite.spec 2>nul

echo Building chat_desensitizer_lite...
pyinstaller --noconfirm --windowed --name chat_desensitizer_lite ^
  --add-data "config;config" ^
  --hidden-import Data_Masking.chat_desensitizer_lite ^
  --hidden-import Data_Masking.chat_parser ^
  --collect-all PyQt5 ^
  Data_Masking\ui\chat_gui_app.py
