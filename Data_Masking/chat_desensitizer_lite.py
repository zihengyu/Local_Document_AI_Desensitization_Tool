#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""lite 聊天脱敏核心逻辑。

冲突统一版本：保留规则优先、NER 可选延迟加载策略。
"""

import json
import os
import pickle
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List, Pattern, Tuple

from Data_Masking.chat_parser import iter_chat_messages


@dataclass
class MatchHit:
    entity_type: str
    original: str
    masked: str
    line_no: int


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resource_base() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return _repo_root()


def _user_data_dir() -> str:
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")

    path = os.path.join(base, "Local_Document_AI_Desensitization_Tool")
    os.makedirs(path, exist_ok=True)
    return path


class ChatDesensitizerLite:
    TOKEN_PATTERN = re.compile(r"__CHAT_MASKED_[a-z_]+_[0-9a-f]{8}__")

    def __init__(
        self,
        mapping_file: str = "",
        whitelist_file: str = "",
        mode_config_file: str = "",
    ):
        default_mapping = os.path.join(_user_data_dir(), "chat_lite_masking_map.pkl")
        default_whitelist = os.path.join(_resource_base(), "config", "whitelist.txt")
        default_mode_config = os.path.join(_resource_base(), "config", "chat_mode.json")

        self.mapping_file = mapping_file or default_mapping
        self.whitelist_file = whitelist_file or default_whitelist
        self.mode_config_file = mode_config_file or default_mode_config

        self.mapping: Dict[str, Tuple[str, str]] = {}
        self.entity_to_mask: Dict[Tuple[str, str], str] = {}

        self.mode_config = self._load_mode_config()
        self.whitelist = self._load_whitelist()
        self._load_mapping()

        self.regex_rules = self._build_regex_rules()
        self.context_rules = self._build_context_rules()

    def _load_mode_config(self) -> Dict:
        default_config = {
            "default_mode": "lite",
            "preview_line_limit": 200,
            "hit_preview_limit": 500,
            "chunk_message_size": 200,
            "strict_max_workers": 1,
        }
        if not os.path.exists(self.mode_config_file):
            return default_config

        with open(self.mode_config_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        default_config.update(loaded)
        return default_config

    def _load_whitelist(self) -> set:
        if not os.path.exists(self.whitelist_file):
            return set()

        with open(self.whitelist_file, "r", encoding="utf-8") as f:
            return {
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            }

    def _load_mapping(self):
        if not os.path.exists(self.mapping_file):
            return

        with open(self.mapping_file, "rb") as f:
            data = pickle.load(f)

        if isinstance(data, tuple) and len(data) == 2:
            self.mapping, self.entity_to_mask = data
        elif isinstance(data, dict):
            self.mapping = data
            self.entity_to_mask = {(orig, etype): key for key, (orig, etype) in self.mapping.items()}

    def _save_mapping(self):
        os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
        with open(self.mapping_file, "wb") as f:
            pickle.dump((self.mapping, self.entity_to_mask), f)

    def clear_mapping(self):
        self.mapping = {}
        self.entity_to_mask = {}
        self._save_mapping()

    def reload_whitelist(self):
        self.whitelist = self._load_whitelist()

    def _build_regex_rules(self) -> Dict[str, Pattern]:
        return {
            "PHONE": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
            "ID_CARD": re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
            "BANK_CARD": re.compile(r"(?<!\d)(?:\d[ -]?){16,19}(?!\d)"),
            "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            "QQ": re.compile(r"(?<!\d)[1-9]\d{6,11}(?!\d)"),
            "PLATE": re.compile(r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}"),
            "ORDER_NO": re.compile(r"(?<![A-Za-z0-9])[A-Z]{0,4}\d{8,24}(?![A-Za-z0-9])"),
        }

    def _build_context_rules(self) -> List[Tuple[str, Pattern]]:
        return [
            ("ACCOUNT", re.compile(r"(?:账号|账户|登录名|user(?:name)?)[：:\s]*([A-Za-z0-9_\-@.]{4,32})", re.I)),
            ("PASSWORD", re.compile(r"(?:密码|pass(?:word)?|口令)[：:\s]*([^\s,，。；;]{4,32})", re.I)),
            ("VERIFY_CODE", re.compile(r"(?:验证码|校验码|动态码)[：:\s]*([A-Za-z0-9]{4,8})", re.I)),
            ("ADDRESS", re.compile(r"(?:地址|收货地址|住址)[：:\s]*([^\n,，;；]{6,80})", re.I)),
            ("WECHAT", re.compile(r"(?:微信号|wx|wechat)[：:\s]*([A-Za-z][-_A-Za-z0-9]{5,19})", re.I)),
            ("TRACKING_NO", re.compile(r"(?:订单号|运单号|合同号|病历号|工号|学号)[：:\s]*([A-Za-z0-9\-]{4,32})", re.I)),
        ]

    def _is_whitelisted(self, value: str) -> bool:
        compact = value.strip()
        return compact in self.whitelist

    def _mask_value(self, value: str, entity_type: str) -> str:
        key = (value, entity_type)
        if key in self.entity_to_mask:
            return self.entity_to_mask[key]

        token = f"__CHAT_MASKED_{entity_type.lower()}_{uuid.uuid4().hex[:8]}__"
        self.entity_to_mask[key] = token
        self.mapping[token] = (value, entity_type)
        return token

    def _apply_rules(self, text: str, line_no: int) -> Tuple[str, List[MatchHit]]:
        masked_text = text
        hits: List[MatchHit] = []

        for entity_type, pattern in self.context_rules:
            for m in list(pattern.finditer(masked_text)):
                value = m.group(1).strip()
                if self._is_whitelisted(value):
                    continue
                token = self._mask_value(value, entity_type)
                masked_text = masked_text.replace(value, token)
                hits.append(MatchHit(entity_type, value, token, line_no))

        for entity_type, pattern in self.regex_rules.items():
            for m in list(pattern.finditer(masked_text)):
                value = m.group(0).strip()
                if len(value) < 6 or self._is_whitelisted(value):
                    continue
                token = self._mask_value(value, entity_type)
                masked_text = masked_text.replace(value, token)
                hits.append(MatchHit(entity_type, value, token, line_no))

        return masked_text, hits

    def _apply_strict_ner(self, text: str, line_no: int) -> Tuple[str, List[MatchHit]]:
        """严格模式可选 NER。仅在调用时才尝试导入和检查模型。"""
        from Data_Masking.NER_model import recognize_entities

        result = recognize_entities(text, save_to_file=False, num_workers=1, enable_parallel=False)
        entities = result.get("output", [])

        masked_text = text
        hits: List[MatchHit] = []

        for ent in entities:
            span = ent.get("span", "").strip()
            etype = str(ent.get("type", "NER"))
            if not span or self._is_whitelisted(span):
                continue
            token = self._mask_value(span, f"NER_{etype}")
            masked_text = masked_text.replace(span, token)
            hits.append(MatchHit(f"NER_{etype}", span, token, line_no))

        return masked_text, hits

    def process_chat_file(
        self,
        input_path: str,
        output_path: str,
        mode: str = "lite",
        strict_enable_ner: bool = False,
    ) -> Dict:
        preview_limit = int(self.mode_config.get("preview_line_limit", 200))
        hit_limit = int(self.mode_config.get("hit_preview_limit", 500))

        preview_lines: List[str] = []
        hit_preview: List[Dict] = []
        total_hits = 0
        total_messages = 0

        with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
            for msg in iter_chat_messages(fin):
                total_messages += 1
                header = f"{msg['timestamp']} '{msg['sender']}'"
                body = msg.get("body", "")

                masked_body, hits = self._apply_rules(body, msg["start_line"])

                if mode == "strict" and strict_enable_ner and masked_body.strip():
                    masked_body, ner_hits = self._apply_strict_ner(masked_body, msg["start_line"])
                    hits.extend(ner_hits)

                fout.write(header + "\n")
                if masked_body:
                    fout.write(masked_body + "\n")
                fout.write("\n")

                total_hits += len(hits)
                for h in hits:
                    if len(hit_preview) < hit_limit:
                        hit_preview.append({
                            "line": h.line_no,
                            "type": h.entity_type,
                            "original": h.original,
                            "masked": h.masked,
                        })

                if len(preview_lines) < preview_limit:
                    preview_lines.extend((header + "\n" + (masked_body or "") + "\n").splitlines())
                    preview_lines = preview_lines[:preview_limit]

        self._save_mapping()

        return {
            "messages": total_messages,
            "hits": total_hits,
            "preview_lines": preview_lines,
            "hit_preview": hit_preview,
            "output_path": output_path,
        }

    def unmask_chat_file(self, input_path: str, output_path: str) -> str:
        with open(input_path, "r", encoding="utf-8") as fin:
            text = fin.read()

        def replace_token(match):
            token = match.group(0)
            if token in self.mapping:
                return self.mapping[token][0]
            return token

        restored = self.TOKEN_PATTERN.sub(replace_token, text)

        with open(output_path, "w", encoding="utf-8") as fout:
            fout.write(restored)

        return output_path
