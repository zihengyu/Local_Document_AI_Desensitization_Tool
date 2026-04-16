@echo off
pyinstaller --noconfirm --windowed --name chat_desensitizer_lite ^
  --add-data "config;config" ^
  Data_Masking\ui\chat_gui_app.py
