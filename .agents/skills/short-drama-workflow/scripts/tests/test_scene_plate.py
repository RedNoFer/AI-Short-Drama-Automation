#!/usr/bin/env python3
"""场景底板的回归自测：空镜通过，人物/车辆/多格进入场景图判错。"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

PLATE = ("真实现场照片，35mm 胶片质感，低饱和，不锐化。16:9 单张全景。画面中无人物。"
         "本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。")


class ScenePlateTest(unittest.TestCase):
    def run_plate(self, prompt: str):
        errors: list[str] = []
        warnings: list[str] = []
        validator.check_scene_plate(
            [{"code": "LOC_01", "kind": "场景", "name": "土路", "prompt": prompt}],
            errors, warnings)
        return errors, warnings

    def test_empty_plate_passes(self):
        errors, warnings = self.run_plate(PLATE)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_person_in_scene_is_error(self):
        errors, _ = self.run_plate("16:9 单张全景。画面中无人物。一个男人站在车门边。")
        self.assertTrue(any("人物" in e for e in errors), errors)

    def test_bare_person_clause_is_error(self):
        errors, _ = self.run_plate("16:9 单张全景。画面中无人物。中景轿车与站在车门边的人。")
        self.assertTrue(any("人物" in e for e in errors), errors)

    def test_vehicle_in_scene_is_error(self):
        errors, _ = self.run_plate("16:9 单张全景。画面中无人物。门前空地停一辆黑色新轿车。")
        self.assertTrue(any("可移动道具" in e for e in errors), errors)

    def test_bare_car_in_scene_is_error(self):
        errors, _ = self.run_plate("16:9 单张全景。画面中无人物。中景路牌与车，远景公路。")
        self.assertTrue(any("可移动道具" in e for e in errors), errors)

    def test_road_lane_is_not_a_car(self):
        errors, _ = self.run_plate(PLATE + "人行道外是车行道，路面湿润。")
        self.assertFalse(any("可移动道具" in e for e in errors), errors)

    def test_negative_car_light_is_not_error(self):
        errors, _ = self.run_plate(PLATE + "本卡画无车灯的自然状态。")
        self.assertFalse(any("可移动道具" in e for e in errors), errors)

    def test_fixed_set_piece_allowed(self):
        errors, _ = self.run_plate(
            "16:9 单张全景。画面中无人物。门前停一辆黑色轿车"
            "（固定陈设，车身与墙留出 2 米净距）。")
        self.assertEqual(errors, [])

    def test_missing_empty_statement_is_error(self):
        errors, _ = self.run_plate("16:9 单张全景。机位站在土路中央。")
        self.assertTrue(any("空镜底板" in e for e in errors), errors)

    def test_missing_plate_role_is_warning(self):
        _, warnings = self.run_plate("16:9 单张全景。画面中无人物。")
        self.assertTrue(any("场景底板" in w for w in warnings), warnings)

    def test_oily_words_are_error(self):
        errors, _ = self.run_plate(PLATE + "庭院里的柚木泛着油润的光。")
        self.assertTrue(any("油润" in e for e in errors), errors)

    def test_negative_wax_is_not_error(self):
        errors, _ = self.run_plate(PLATE + "木材干哑，不打蜡。")
        self.assertFalse(any("打蜡" in e for e in errors), errors)

    def test_occupation_word_is_error(self):
        errors, _ = self.run_plate(PLATE + "中景盐堆与弯腰作业的盐工剪影。")
        self.assertTrue(any("人物" in e for e in errors), errors)

    def test_nurse_station_is_not_a_person(self):
        errors, _ = self.run_plate(PLATE + "走廊尽头是护士站。")
        self.assertFalse(any("人物" in e for e in errors), errors)

    def test_policy_can_extend_person_words(self):
        policy = {"assets": {"scene_prompt": {"person_pattern": "掌柜"}}}
        errors: list[str] = []
        warnings: list[str] = []
        validator.check_scene_plate(
            [{"code": "LOC_01", "kind": "场景", "name": "柜台",
              "prompt": PLATE + "柜台后站着掌柜。"}],
            errors, warnings, policy)
        self.assertTrue(any("人物" in e for e in errors), errors)

    def test_missing_realism_anchor_is_warning(self):
        _, warnings = self.run_plate(
            "16:9 单张全景。画面中无人物。本卡是场景底板：只锁空间、光位与材质。")
        self.assertTrue(any("真实感锚" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
