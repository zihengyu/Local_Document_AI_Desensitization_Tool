#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""聊天 TXT 解析器（lite 子应用）。"""

import re
from typing import Dict, Generator, List, TextIO

HEADER_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) '([^']+)'\s*$")


def iter_chat_messages(file_obj: TextIO) -> Generator[Dict, None, None]:
    """按流式方式解析聊天消息。

    支持格式：
    YYYY-MM-DD HH:MM:SS '发送者'
    正文(1~多行)
    """
    current = None
    body_lines: List[str] = []

    for line_no, raw_line in enumerate(file_obj, start=1):
        line = raw_line.rstrip("\n")
        match = HEADER_PATTERN.match(line.strip())

        if match:
            if current is not None:
                current["body"] = "\n".join(body_lines).strip("\n")
                current["end_line"] = line_no - 1
                yield current

            current = {
                "timestamp": match.group(1),
                "sender": match.group(2),
                "start_line": line_no,
                "end_line": line_no,
                "body": "",
            }
            body_lines = []
            continue

        if current is None:
            # 跳过消息头之前的噪音行
            continue

        body_lines.append(line)

    if current is not None:
        current["body"] = "\n".join(body_lines).strip("\n")
        current["end_line"] = current["start_line"] + len(body_lines)
        yield current
