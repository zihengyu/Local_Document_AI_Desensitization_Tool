#!/bin/bash
set -e

rm -rf build dist chat_desensitizer_lite.spec

# 在 macOS 上优先尝试 universal2，若当前 Python 不支持则回退到本机架构
TARGET_ARCH="universal2"
if ! python - <<'PY'
import platform
print(platform.machine())
PY
then
  TARGET_ARCH=""
fi

COMMON_ARGS=(
  --noconfirm
  --windowed
  --name chat_desensitizer_lite
  --osx-bundle-identifier com.localdesensitizer.chatlite
  --add-data "config:config"
  --hidden-import Data_Masking.chat_desensitizer_lite
  --hidden-import Data_Masking.chat_parser
  --collect-all PyQt5
  Data_Masking/ui/chat_gui_app.py
)

if pyinstaller --help | rg -q "target-arch"; then
  if pyinstaller --noconfirm --windowed --name _arch_check --target-arch universal2 Data_Masking/ui/chat_gui_app.py >/dev/null 2>&1; then
    rm -rf build dist _arch_check.spec
    pyinstaller "${COMMON_ARGS[@]}" --target-arch universal2
  else
    echo "[WARN] 当前 Python/PyInstaller 不支持 universal2，回退到本机架构打包。"
    pyinstaller "${COMMON_ARGS[@]}"
  fi
else
  pyinstaller "${COMMON_ARGS[@]}"
fi
