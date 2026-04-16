#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from typing import Dict

# 冲突统一版本：保持独立 lite GUI 入口，不依赖主文档流程

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QComboBox,
)

from Data_Masking.chat_desensitizer_lite import ChatDesensitizerLite


class ChatWorker(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, app_ref, action: str):
        super().__init__()
        self.app_ref = app_ref
        self.action = action

    def run(self):
        try:
            if self.action == "mask":
                result = self.app_ref.processor.process_chat_file(
                    input_path=self.app_ref.input_file.text().strip(),
                    output_path=self.app_ref.output_file.text().strip(),
                    mode=self.app_ref.mode_combo.currentData(),
                    strict_enable_ner=self.app_ref.strict_ner_checkbox.isChecked(),
                )
            else:
                out = self.app_ref.processor.unmask_chat_file(
                    self.app_ref.input_file.text().strip(),
                    self.app_ref.output_file.text().strip(),
                )
                result = {"output_path": out, "preview_lines": [], "hit_preview": [], "messages": 0, "hits": 0}
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class ChatLiteWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processor = ChatDesensitizerLite()
        self.worker = None
        self.setWindowTitle("聊天 TXT 脱敏工具（Lite）")
        self.resize(1080, 760)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        form = QGridLayout()
        self.input_file = QLineEdit()
        self.output_file = QLineEdit()
        in_btn = QPushButton("选择输入 txt")
        out_btn = QPushButton("选择输出文件")
        in_btn.clicked.connect(self.pick_input)
        out_btn.clicked.connect(self.pick_output)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("极速模式（默认）", "lite")
        self.mode_combo.addItem("严格模式", "strict")

        self.strict_ner_checkbox = QCheckBox("严格模式启用 NER（可选，较慢）")

        form.addWidget(QLabel("输入文件"), 0, 0)
        form.addWidget(self.input_file, 0, 1)
        form.addWidget(in_btn, 0, 2)

        form.addWidget(QLabel("输出文件"), 1, 0)
        form.addWidget(self.output_file, 1, 1)
        form.addWidget(out_btn, 1, 2)

        form.addWidget(QLabel("模式"), 2, 0)
        form.addWidget(self.mode_combo, 2, 1)
        form.addWidget(self.strict_ner_checkbox, 2, 2)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        mask_btn = QPushButton("开始脱敏")
        unmask_btn = QPushButton("恢复原文")
        clear_btn = QPushButton("清空映射")
        reload_wl_btn = QPushButton("重载白名单")

        mask_btn.clicked.connect(lambda: self.start_job("mask"))
        unmask_btn.clicked.connect(lambda: self.start_job("unmask"))
        clear_btn.clicked.connect(self.clear_mapping)
        reload_wl_btn.clicked.connect(self.reload_whitelist)

        btn_row.addWidget(mask_btn)
        btn_row.addWidget(unmask_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(reload_wl_btn)
        root.addLayout(btn_row)

        self.summary_label = QLabel("状态：待处理")
        root.addWidget(self.summary_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("仅显示前 200 行预览")
        root.addWidget(QLabel("输出预览（前 200 行）"))
        root.addWidget(self.preview)

        self.hit_table = QTableWidget(0, 4)
        self.hit_table.setHorizontalHeaderLabels(["行号", "类型", "原文", "脱敏后"])
        root.addWidget(QLabel("命中详情（前 500 条）"))
        root.addWidget(self.hit_table)

        self.setCentralWidget(central)

    def pick_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择聊天 txt", "", "Text Files (*.txt)")
        if path:
            self.input_file.setText(path)
            if not self.output_file.text().strip():
                base, ext = os.path.splitext(path)
                self.output_file.setText(f"{base}_masked{ext}")

    def pick_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存输出文件", "", "Text Files (*.txt)")
        if path:
            self.output_file.setText(path)

    def start_job(self, action: str):
        if not self.input_file.text().strip() or not self.output_file.text().strip():
            QMessageBox.warning(self, "提示", "请先选择输入和输出文件")
            return

        self.summary_label.setText("状态：处理中...")
        self.worker = ChatWorker(self, action)
        self.worker.finished_signal.connect(self.on_job_done)
        self.worker.error_signal.connect(self.on_job_error)
        self.worker.start()

    def on_job_done(self, result: Dict):
        self.summary_label.setText(
            f"状态：完成。消息 {result.get('messages', 0)} 条，命中 {result.get('hits', 0)} 项，输出：{result.get('output_path', '')}"
        )

        preview_lines = result.get("preview_lines", [])
        self.preview.setPlainText("\n".join(preview_lines))

        hits = result.get("hit_preview", [])
        self.hit_table.setRowCount(len(hits))
        for row, item in enumerate(hits):
            self.hit_table.setItem(row, 0, QTableWidgetItem(str(item.get("line", ""))))
            self.hit_table.setItem(row, 1, QTableWidgetItem(item.get("type", "")))
            self.hit_table.setItem(row, 2, QTableWidgetItem(item.get("original", "")))
            self.hit_table.setItem(row, 3, QTableWidgetItem(item.get("masked", "")))

        QMessageBox.information(self, "完成", "处理完成")

    def on_job_error(self, error: str):
        self.summary_label.setText("状态：失败")
        QMessageBox.critical(self, "处理失败", error)

    def clear_mapping(self):
        self.processor.clear_mapping()
        QMessageBox.information(self, "完成", "映射已清空")

    def reload_whitelist(self):
        self.processor.reload_whitelist()
        QMessageBox.information(self, "完成", "白名单已重载")


def main():
    app = QApplication(sys.argv)
    window = ChatLiteWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
