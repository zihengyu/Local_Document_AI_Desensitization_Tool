#!/bin/bash
set -e

rm -rf build dist chat_desensitizer_lite.spec

if ! python -c "import PyQt5" >/dev/null 2>&1; then
  echo "[ERROR] 当前 Python 环境未安装 PyQt5。"
  echo "[HINT] 请先执行: python -m pip install PyQt5"
  exit 1
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

# 优先构建 universal2；失败则回退本机架构，避免工具链冲突
if python -m PyInstaller --noconfirm --windowed --name _arch_check --target-arch universal2 Data_Masking/ui/chat_gui_app.py >/dev/null 2>&1; then
  rm -rf build dist _arch_check.spec
  python -m PyInstaller "${COMMON_ARGS[@]}" --target-arch universal2
else
  echo "[WARN] universal2 构建不可用，回退到本机架构。"
  rm -rf build dist _arch_check.spec
  python -m PyInstaller "${COMMON_ARGS[@]}"
fi
