#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from typing import Dict

# 冲突统一版本：保持独立 lite GUI 入口，不依赖主文档流程

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
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
                    enabled_rule_ids=self.app_ref.pending_enabled_rule_ids,
                    custom_rules=self.app_ref.pending_custom_rules,
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
        self.rule_checkboxes = {}
        self.pending_enabled_rule_ids = []
        self.pending_custom_rules = []
        self.setWindowTitle("聊天 TXT 脱敏工具（Lite）")
        self.resize(1380, 860)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("聊天 TXT 脱敏工具（Lite）")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        root.addWidget(main_splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        io_group = QGroupBox("任务设置")
        io_layout = QGridLayout(io_group)

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

        io_layout.addWidget(QLabel("输入文件"), 0, 0)
        io_layout.addWidget(self.input_file, 0, 1)
        io_layout.addWidget(in_btn, 0, 2)

        io_layout.addWidget(QLabel("输出文件"), 1, 0)
        io_layout.addWidget(self.output_file, 1, 1)
        io_layout.addWidget(out_btn, 1, 2)

        io_layout.addWidget(QLabel("模式"), 2, 0)
        io_layout.addWidget(self.mode_combo, 2, 1)
        io_layout.addWidget(self.strict_ner_checkbox, 2, 2)
        left_layout.addWidget(io_group)

        rules_group = QGroupBox("脱敏规则与自定义")
        rules_layout = QVBoxLayout(rules_group)
        rules_layout.addWidget(QLabel("默认规则默认全选，可按需取消。自定义规则填写“规则名称 + 正则表达式”，若正则含捕获组则脱敏第 1 个捕获组。"))

        default_grid = QGridLayout()
        for index, rule in enumerate(self.processor.get_default_rule_definitions()):
            checkbox = QCheckBox(f"{rule['label']}：{rule['description']}")
            checkbox.setChecked(True)
            self.rule_checkboxes[rule["id"]] = checkbox
            default_grid.addWidget(checkbox, index // 2, index % 2)
        rules_layout.addLayout(default_grid)

        custom_label_row = QHBoxLayout()
        custom_label_row.addWidget(QLabel("自定义规则"))
        add_custom_btn = QPushButton("新增规则")
        remove_custom_btn = QPushButton("删除选中")
        add_custom_btn.clicked.connect(self.add_custom_rule_row)
        remove_custom_btn.clicked.connect(self.remove_selected_custom_rules)
        custom_label_row.addStretch(1)
        custom_label_row.addWidget(add_custom_btn)
        custom_label_row.addWidget(remove_custom_btn)
        rules_layout.addLayout(custom_label_row)

        self.custom_rule_table = QTableWidget(0, 2)
        self.custom_rule_table.setHorizontalHeaderLabels(["规则名称", "正则表达式"])
        self.custom_rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.custom_rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_rule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.custom_rule_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.custom_rule_table.setMinimumHeight(180)
        self.custom_rule_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.custom_rule_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        rules_layout.addWidget(self.custom_rule_table)
        left_layout.addWidget(rules_group, 1)

        btn_row = QHBoxLayout()
        mask_btn = QPushButton("开始脱敏")
        unmask_btn = QPushButton("恢复原文")
        clear_btn = QPushButton("清空映射")
        reload_wl_btn = QPushButton("重载白名单")
        import_wl_btn = QPushButton("导入白名单")
        wl_format_btn = QPushButton("白名单格式")
        tools_help_btn = QPushButton("功能说明")

        mask_btn.clicked.connect(lambda: self.start_job("mask"))
        unmask_btn.clicked.connect(lambda: self.start_job("unmask"))
        clear_btn.clicked.connect(self.clear_mapping)
        reload_wl_btn.clicked.connect(self.reload_whitelist)
        import_wl_btn.clicked.connect(self.import_whitelist)
        wl_format_btn.clicked.connect(self.show_whitelist_format)
        tools_help_btn.clicked.connect(self.show_tool_explanations)

        clear_btn.setToolTip("清空历史脱敏映射。清空后，旧的脱敏文件可能无法恢复原文。")
        reload_wl_btn.setToolTip("重新读取当前 whitelist.txt。适合你手动修改白名单文件后立即刷新。")
        import_wl_btn.setToolTip("从外部 txt 文件导入白名单条目，并立即写入当前 whitelist.txt。")
        wl_format_btn.setToolTip("查看 whitelist.txt 的格式要求和示例。")

        btn_row.addWidget(mask_btn)
        btn_row.addWidget(unmask_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(reload_wl_btn)
        btn_row.addWidget(import_wl_btn)
        btn_row.addWidget(wl_format_btn)
        btn_row.addWidget(tools_help_btn)
        left_layout.addLayout(btn_row)

        self.summary_label = QLabel("状态：待处理")
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)
        left_layout.addStretch(1)

        results_splitter = QSplitter(Qt.Vertical)
        results_splitter.setChildrenCollapsible(False)

        preview_group = QGroupBox("输出预览（前 200 行）")
        preview_layout = QVBoxLayout(preview_group)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("仅显示前 200 行预览")
        self.preview.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.preview.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preview_layout.addWidget(self.preview)
        results_splitter.addWidget(preview_group)

        hits_group = QGroupBox("命中详情（前 500 条）")
        hits_layout = QVBoxLayout(hits_group)
        self.hit_table = QTableWidget(0, 4)
        self.hit_table.setHorizontalHeaderLabels(["行号", "类型", "原文", "脱敏后"])
        self.hit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.hit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.hit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.hit_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.hit_table.setAlternatingRowColors(True)
        self.hit_table.setWordWrap(False)
        self.hit_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.hit_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        hits_layout.addWidget(self.hit_table)
        results_splitter.addWidget(hits_group)

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(results_splitter)
        main_splitter.setSizes([520, 840])
        results_splitter.setSizes([360, 420])

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

    def import_whitelist(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入白名单文件", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return

        try:
            result = self.processor.import_whitelist(path)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))
            return

        QMessageBox.information(
            self,
            "导入完成",
            (
                f"白名单已导入。\n"
                f"来源文件：{path}\n"
                f"读取条目：{result['imported']} 条\n"
                f"新增条目：{result['added']} 条\n"
                f"当前总条目：{result['total']} 条"
            ),
        )

    def show_tool_explanations(self):
        QMessageBox.information(
            self,
            "功能说明",
            (
                "清空映射：删除当前保存的“脱敏占位符 <-> 原文”对应关系。清空后，历史脱敏文件可能无法再完整恢复原文。\n\n"
                "重载白名单：重新读取当前 whitelist.txt 内容。适合你手动编辑白名单文件后立即刷新。\n\n"
                "导入白名单：从外部 txt 文件读取条目并合并到当前 whitelist.txt，导入后立即生效。"
            ),
        )

    def show_whitelist_format(self):
        QMessageBox.information(
            self,
            "白名单格式",
            (
                "白名单文件是 UTF-8 编码的纯文本，每行一个条目。\n"
                "空行会被忽略，以 # 开头的行会被当作注释忽略。\n\n"
                "示例：\n"
                "# 公司内部固定术语\n"
                "OpenAI\n"
                "北京市海淀区\n"
                "客服热线\n"
                "A12\n\n"
                "说明：\n"
                "1. 每行写一个不希望被脱敏的完整词条。\n"
                "2. 不支持在白名单里写正则表达式。\n"
                "3. 只有完全匹配白名单的内容才会跳过脱敏。"
            ),
        )

    def add_custom_rule_row(self):
        row = self.custom_rule_table.rowCount()
        self.custom_rule_table.insertRow(row)
        self.custom_rule_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_rule_table.setItem(row, 1, QTableWidgetItem(""))
        self.custom_rule_table.setCurrentCell(row, 0)

    def remove_selected_custom_rules(self):
        current_row = self.custom_rule_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的自定义规则")
            return
        self.custom_rule_table.removeRow(current_row)

    def get_enabled_rule_ids(self):
        return [rule_id for rule_id, checkbox in self.rule_checkboxes.items() if checkbox.isChecked()]

    def get_custom_rules(self):
        custom_rules = []
        for row in range(self.custom_rule_table.rowCount()):
            name_item = self.custom_rule_table.item(row, 0)
            pattern_item = self.custom_rule_table.item(row, 1)
            name = name_item.text().strip() if name_item and name_item.text() else ""
            pattern = pattern_item.text().strip() if pattern_item and pattern_item.text() else ""

            if not name and not pattern:
                continue
            if not name or not pattern:
                raise ValueError(f"第 {row + 1} 条自定义规则需要同时填写规则名称和正则表达式")

            custom_rules.append({"name": name, "pattern": pattern})
        return custom_rules

    def start_job(self, action: str):
        if not self.input_file.text().strip() or not self.output_file.text().strip():
            QMessageBox.warning(self, "提示", "请先选择输入和输出文件")
            return

        try:
            custom_rules = self.get_custom_rules() if action == "mask" else []
        except ValueError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            return

        enabled_rule_ids = self.get_enabled_rule_ids() if action == "mask" else []
        if action == "mask" and not enabled_rule_ids and not custom_rules:
            QMessageBox.warning(self, "提示", "请至少启用一条默认规则，或添加一条自定义规则")
            return

        self.pending_enabled_rule_ids = enabled_rule_ids
        self.pending_custom_rules = custom_rules
        self.summary_label.setText("状态：处理中...")
        self.worker = ChatWorker(self, action)
        self.worker.finished_signal.connect(self.on_job_done)
        self.worker.error_signal.connect(self.on_job_error)
        self.worker.start()


def main():
    app = QApplication(sys.argv)
    window = ChatLiteWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
