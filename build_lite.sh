#!/bin/bash
set -e

rm -rf build dist chat_desensitizer_lite.spec

pyinstaller --noconfirm --windowed --name chat_desensitizer_lite \
  --target-arch universal2 \
  --osx-bundle-identifier com.localdesensitizer.chatlite \
  --add-data "config:config" \
  Data_Masking/ui/chat_gui_app.py
