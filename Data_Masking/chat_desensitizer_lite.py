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
    DEFAULT_RULE_DEFINITIONS = [
        {"id": "ACCOUNT", "entity_type": "ACCOUNT", "label": "账号", "description": "识别账号、账户、用户名等字段后的值", "pattern": r"(?:账号|账户|登录名|user(?:name)?)[：:\s]*([A-Za-z0-9_\-@.]{4,32})", "group": 1},
        {"id": "PASSWORD", "entity_type": "PASSWORD", "label": "密码", "description": "识别密码、口令等字段后的值", "pattern": r"(?:密码|pass(?:word)?|口令)[：:\s]*([^\s,，。；;]{4,32})", "group": 1},
        {"id": "VERIFY_CODE", "entity_type": "VERIFY_CODE", "label": "验证码", "description": "识别验证码、校验码、动态码后的值", "pattern": r"(?:验证码|校验码|动态码)[：:\s]*([A-Za-z0-9]{4,8})", "group": 1},
        {"id": "ADDRESS", "entity_type": "ADDRESS", "label": "地址", "description": "识别地址、住址、收货地址后的文本", "pattern": r"(?:地址|收货地址|住址)[：:\s]*([^\n,，;；]{6,80})", "group": 1},
        {"id": "WECHAT", "entity_type": "WECHAT", "label": "微信号", "description": "识别微信号字段后的值", "pattern": r"(?:微信号|wx|wechat)[：:\s]*([A-Za-z][-_A-Za-z0-9]{5,19})", "group": 1},
        {"id": "TRACKING_NO", "entity_type": "TRACKING_NO", "label": "编号", "description": "识别订单号、运单号、合同号、病历号、工号、学号后的值", "pattern": r"(?:订单号|运单号|合同号|病历号|工号|学号)[：:\s]*([A-Za-z0-9\-]{4,32})", "group": 1},
        {"id": "PHONE", "entity_type": "PHONE", "label": "手机号", "description": "识别中国大陆手机号", "pattern": r"(?<!\d)1[3-9]\d{9}(?!\d)", "group": 0, "min_length": 6},
        {"id": "ID_CARD", "entity_type": "ID_CARD", "label": "身份证号", "description": "识别 18 位身份证号", "pattern": r"(?<!\d)\d{17}[0-9Xx](?!\d)", "group": 0, "min_length": 6},
        {"id": "BANK_CARD", "entity_type": "BANK_CARD", "label": "银行卡号", "description": "识别 16 到 19 位银行卡号", "pattern": r"(?<!\d)(?:\d[ -]?){16,19}(?!\d)", "group": 0, "min_length": 6},
        {"id": "EMAIL", "entity_type": "EMAIL", "label": "邮箱", "description": "识别邮箱地址", "pattern": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "group": 0, "min_length": 6},
        {"id": "QQ", "entity_type": "QQ", "label": "QQ 号", "description": "识别 7 到 12 位 QQ 号", "pattern": r"(?<!\d)[1-9]\d{6,11}(?!\d)", "group": 0, "min_length": 6},
        {"id": "PLATE", "entity_type": "PLATE", "label": "车牌号", "description": "识别常见车牌号", "pattern": r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}", "group": 0, "min_length": 6},
        {"id": "ORDER_NO", "entity_type": "ORDER_NO", "label": "通用订单号", "description": "识别字母加数字的长编号", "pattern": r"(?<![A-Za-z0-9])[A-Z]{0,4}\d{8,24}(?![A-Za-z0-9])", "group": 0, "min_length": 6},
    ]

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

        self.default_rules = self._compile_default_rules()

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

    def import_whitelist(self, source_path: str) -> Dict[str, int]:
        if not source_path or not os.path.exists(source_path):
            raise FileNotFoundError("白名单文件不存在")

        imported_items = []
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                item = line.strip()
                if item and not item.startswith("#"):
                    imported_items.append(item)

        existing = set(self.whitelist)
        merged = existing.union(imported_items)

        os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
        with open(self.whitelist_file, "w", encoding="utf-8") as f:
            for item in sorted(merged):
                f.write(item + "\n")

        self.whitelist = merged
        return {
            "imported": len(imported_items),
            "added": len(merged - existing),
            "total": len(merged),
        }

    def _compile_default_rules(self) -> Dict[str, Dict]:
        compiled = {}
        for item in self.DEFAULT_RULE_DEFINITIONS:
            compiled[item["id"]] = {
                **item,
                "compiled": re.compile(item["pattern"], re.I),
            }
        return compiled

    def get_default_rule_definitions(self) -> List[Dict[str, str]]:
        return [
            {
                "id": item["id"],
                "entity_type": item["entity_type"],
                "label": item["label"],
                "description": item["description"],
            }
            for item in self.DEFAULT_RULE_DEFINITIONS
        ]

    def _token_entity_slug(self, entity_type: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", entity_type.lower())
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug or "custom"

    def _build_active_rules(self, enabled_rule_ids=None, custom_rules=None) -> Tuple[List[Dict], List[Dict]]:
        if enabled_rule_ids is None:
            enabled_rule_ids = [item["id"] for item in self.DEFAULT_RULE_DEFINITIONS]

        enabled = set(enabled_rule_ids)
        context_rules: List[Dict] = []
        regex_rules: List[Dict] = []

        for rule_id in enabled_rule_ids:
            if rule_id not in enabled or rule_id not in self.default_rules:
                continue
            rule = self.default_rules[rule_id]
            target = context_rules if rule["group"] else regex_rules
            target.append(rule)

        for index, rule in enumerate(custom_rules or [], start=1):
            name = str(rule.get("name", "")).strip() or f"自定义规则{index}"
            pattern_text = str(rule.get("pattern", "")).strip()
            if not pattern_text:
                continue
            try:
                compiled = re.compile(pattern_text, re.I)
            except re.error as exc:
                raise ValueError(f"自定义规则“{name}”正则无效：{exc}") from exc

            target = context_rules if compiled.groups else regex_rules
            target.append({
                "id": f"CUSTOM_{index}",
                "entity_type": name,
                "label": name,
                "description": "用户自定义规则",
                "pattern": pattern_text,
                "group": 1 if compiled.groups else 0,
                "min_length": 0,
                "compiled": compiled,
            })

        return context_rules, regex_rules

    def _is_whitelisted(self, value: str) -> bool:
        compact = value.strip()
        return compact in self.whitelist

    def _mask_value(self, value: str, entity_type: str) -> str:
        key = (value, entity_type)
        if key in self.entity_to_mask:
            return self.entity_to_mask[key]

        token = f"__CHAT_MASKED_{self._token_entity_slug(entity_type)}_{uuid.uuid4().hex[:8]}__"
        self.entity_to_mask[key] = token
        self.mapping[token] = (value, entity_type)
        return token

    def _apply_rules(self, text: str, line_no: int, enabled_rule_ids=None, custom_rules=None) -> Tuple[str, List[MatchHit]]:
        masked_text = text
        hits: List[MatchHit] = []
        context_rules, regex_rules = self._build_active_rules(enabled_rule_ids=enabled_rule_ids, custom_rules=custom_rules)

        for rule in context_rules:
            for m in list(rule["compiled"].finditer(masked_text)):
                value = m.group(rule["group"]).strip()
                if self._is_whitelisted(value):
                    continue
                token = self._mask_value(value, rule["entity_type"])
                masked_text = masked_text.replace(value, token)
                hits.append(MatchHit(rule["entity_type"], value, token, line_no))

        for rule in regex_rules:
            for m in list(rule["compiled"].finditer(masked_text)):
                value = m.group(rule["group"]).strip()
                if len(value) < int(rule.get("min_length", 6)) or self._is_whitelisted(value):
                    continue
                token = self._mask_value(value, rule["entity_type"])
                masked_text = masked_text.replace(value, token)
                hits.append(MatchHit(rule["entity_type"], value, token, line_no))

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
        enabled_rule_ids=None,
        custom_rules=None,
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

                masked_body, hits = self._apply_rules(
                    body,
                    msg["start_line"],
                    enabled_rule_ids=enabled_rule_ids,
                    custom_rules=custom_rules,
                )

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
