#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

rm -rf build dist chat_desensitizer_lite.spec

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "[ERROR] 未找到可用的 Python 解释器。"
    echo "[HINT] 请先安装 Python 3，或通过 PYTHON_BIN 指定解释器路径。"
    exit 1
  fi
fi

export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$SCRIPT_DIR/.pyinstaller}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$SCRIPT_DIR/.matplotlib}"
mkdir -p "$PYINSTALLER_CONFIG_DIR" "$MPLCONFIGDIR"

if ! "$PYTHON_BIN" -c "import PyQt5" >/dev/null 2>&1; then
  echo "[ERROR] 当前 Python 环境未安装 PyQt5。"
  echo "[HINT] 请先执行: $PYTHON_BIN -m pip install PyQt5"
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
if "$PYTHON_BIN" -m PyInstaller --noconfirm --windowed --name _arch_check --target-arch universal2 Data_Masking/ui/chat_gui_app.py >/dev/null 2>&1; then
  rm -rf build dist _arch_check.spec
  "$PYTHON_BIN" -m PyInstaller "${COMMON_ARGS[@]}" --target-arch universal2
else
  echo "[WARN] universal2 构建不可用，回退到本机架构。"
  rm -rf build dist _arch_check.spec
  "$PYTHON_BIN" -m PyInstaller "${COMMON_ARGS[@]}"
fi
