#!/usr/bin/env python3
"""旧式展开包校验器必须只接受显式 Seedance 2.5 轨。"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "delivery_validator", ROOT / "scripts" / "validate_delivery.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class LegacyDeliveryBranchTests(unittest.TestCase):
    def test_missing_or_non_seedance_model_fails_before_length_check(self):
        for clip in (
            {"id": "C01"},
            {"id": "C01", "model": "Wan3.0"},
            {"id": "C01", "model": "H3"},
        ):
            with self.subTest(clip=clip):
                errors: list[str] = []
                stats = validator.validate_clip(
                    clip, Path("."), {}, {"default_duration_sec": 30}, errors)
                self.assertEqual(stats, {"id": "C01"})
                self.assertEqual(len(errors), 1)
                self.assertIn("旧式 Seedance 2.5 展开包校验器", errors[0])
                self.assertNotIn("字符", errors[0])

    def test_seedance_model_is_allowed_to_continue(self):
        errors: list[str] = []
        stats = validator.validate_clip(
            {"id": "C01", "model": "Seedance 2.5"}, Path("."), {},
            {"default_duration_sec": 30}, errors)
        self.assertEqual(stats["id"], "C01")
        self.assertFalse(any("旧式 Seedance" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
