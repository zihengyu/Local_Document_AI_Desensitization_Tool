@echo off
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /f /q chat_desensitizer_lite.spec 2>nul

pyinstaller --noconfirm --windowed --name chat_desensitizer_lite ^
  --add-data "config;config" ^
  Data_Masking\ui\chat_gui_app.py
