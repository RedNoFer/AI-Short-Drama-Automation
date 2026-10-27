#!/usr/bin/env python3
"""角色一致性 / 参考预算 / 服装锚 的回归自测（WAN30-08/09、OUTFIT-03）。"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

CHARS = {"CHAR_01": "阿泽（全队领队）", "CHAR_02": "苏晚（全队观察者）"}


def shot(code: str, consistency: str, props: list[str] | None = None) -> dict:
    return {
        "code": code,
        "bindings": {"角色": ["CHAR_01"], "道具": props or []},
        "prompts": {"视频提示词": f"【公共总规范】画风……【角色一致性】{consistency}【表演核心】……"},
    }


def run(shots: list[dict]) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    stats = validator.check_identity_and_reference_budget(
        [{"code": "E01", "shots": shots}], CHARS, errors, warnings)
    return errors, warnings, stats


class IdentityConsistencyTest(unittest.TestCase):
    def test_same_anchors_pass(self):
        text = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣／黑机能长裤／登山靴。"
        errors, warnings, stats = run([shot("SH01", text), shot("SH02", text)])
        self.assertNotIn("anchor_missing_lower", stats)
        self.assertFalse([w for w in warnings if "WAN30-09" in w])

    def test_two_versions_warn(self):
        a = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣／黑机能长裤／登山靴。"
        b = "阿泽：身份外观遵循 CHAR_01 人物参考图。"
        errors, warnings, stats = run([shot("SH01", a), shot("SH02", b)])
        self.assertTrue(any("WAN30-09" in w for w in warnings))

    def test_full_body_reference_means_video_anchor_omits_lower_garment(self):
        text = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣。"
        errors, warnings, stats = run([shot("SH01", text)])
        self.assertNotIn("anchor_missing_lower", stats)
        self.assertFalse(any("OUTFIT-03" in w for w in warnings))

    def test_above_recommended_six_warns_but_is_not_over_budget(self):
        text = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣／黑机能长裤／登山靴。"
        errors, warnings, stats = run([shot("SH01", text, props=[f"PROP_0{i}" for i in range(1, 7)])])
        self.assertFalse(errors)
        self.assertEqual(stats["above_recommended"], 1)
        self.assertEqual(stats["over_budget"], 0)
        self.assertTrue(any("WAN30-08" in w for w in warnings))

    def test_ten_reference_images_are_within_wan30_hard_limit(self):
        text = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣／黑机能长裤／登山靴。"
        errors, _, stats = run([shot("SH01", text, props=[f"PROP_{i:02d}" for i in range(1, 10)])])
        self.assertFalse(errors)
        self.assertEqual(stats["over_budget"], 0)

    def test_more_than_ten_reference_images_is_blocking(self):
        text = "阿泽：黑色碎短发／旧手绳／深灰冲锋衣／黑机能长裤／登山靴。"
        errors, _, stats = run([shot("SH01", text, props=[f"PROP_{i:02d}" for i in range(1, 11)])])
        self.assertEqual(stats["over_budget"], 1)
        self.assertTrue(any("硬上限 10 张" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
