#!/usr/bin/env python3
"""audit_h3_prompt.py 的回归自测：官方范例必须通过，反例必须报错。

运行：python3 .agents/skills/minimax-h3-adapter/scripts/tests/test_audit_h3_prompt.py
官方原文范例路径：25 minimax H3官方skill/skills/h3-prompt-writing/references/
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
REPO = SKILL_DIR.parents[2]
spec = importlib.util.spec_from_file_location("audit_h3", SKILL_DIR / "scripts" / "audit_h3_prompt.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
POLICY = json.loads((REPO / ".agents/skills/short-drama-workflow/policy.json").read_text(encoding="utf-8"))

BASE_REF = REPO / "25 minimax H3官方skill/skills/h3-prompt-writing/references/base-en.txt"
REF_REF = REPO / "25 minimax H3官方skill/skills/h3-prompt-writing/references/ref-en.txt"


def official_cases():
    base = BASE_REF.read_text(encoding="utf-8")
    blocks = re.findall(r"```text\n(.*?)```", base, re.S)[-4:]
    ref = REF_REF.read_text(encoding="utf-8")
    full = re.findall(r"```text\n(.*?)```", ref, re.S)[-1]
    return list(zip(["t2va", "i2va", "fl2va", "l2va"], blocks)) + [("ref2va", full)]


class AuditH3Tests(unittest.TestCase):
    def test_official_examples_pass(self):
        for mode, body in official_cases():
            with self.subTest(mode=mode):
                result = audit.audit(body, mode, 15, POLICY)
                self.assertTrue(result["ok"], f"{mode}: {result['errors']}")

    def test_missing_field_rejected(self):
        body = "integrated_multimodal_description: [Shot 1] A man stands in the rain."
        result = audit.audit(body, "t2va", 10, POLICY)
        self.assertFalse(result["ok"])

    def test_cut_beyond_duration_rejected(self):
        body = ("integrated_multimodal_description: [Shot 1] A man stands in the rain. "
                "[Shot 2] At 00:20.000, the camera cuts to the door.\n\n"
                "overall_soundscape: Rain falls on the pavement outside.\n\n"
                "non_diegetic_music: N/A")
        result = audit.audit(body, "t2va", 10, POLICY)
        self.assertFalse(result["ok"])

    def test_dialogue_without_language_tag_rejected(self):
        body = ("integrated_multimodal_description: [Shot 1] A man says: <d>I left.</d>\n\n"
                "overall_soundscape: Rain falls on the pavement outside.\n\n"
                "non_diegetic_music: N/A")
        result = audit.audit(body, "t2va", 10, POLICY)
        self.assertFalse(result["ok"])

    def test_over_char_limit_rejected(self):
        filler = " The camera holds on the empty road while the fog thins." * 150
        body = ("integrated_multimodal_description: [Shot 1] A man stands in the rain."
                + filler + "\n\n"
                "overall_soundscape: Rain falls on the pavement outside.\n\n"
                "non_diegetic_music: N/A")
        result = audit.audit(body, "t2va", 10, POLICY)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
