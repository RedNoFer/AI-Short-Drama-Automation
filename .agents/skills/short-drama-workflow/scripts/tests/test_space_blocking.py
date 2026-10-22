#!/usr/bin/env python3
"""validate_space_blocking.py 的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_space_blocking.py
新增或修改站位校验规则时先跑本测试。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "space_blocking", ROOT / "scripts" / "validate_space_blocking.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

BASE = {
    "version": "1.0",
    "scene": {"name": "小院堂屋", "environment": "农村堂屋", "time": "夜晚",
              "scale": "meters"},
    "characters": [
        {"id": "char_lxm", "name": "林小满", "color": "#d84a3a",
         "position": [0, 0, 1.2], "facing": 0.0, "posePreset": "stand"},
        {"id": "char_sw", "name": "苏晚", "color": "#3a7ad8",
         "position": [0, 0.45, -1.6], "facing": 3.1416, "posePreset": "sit"},
    ],
    "props": [
        {"id": "prop_table", "name": "长桌", "kind": "table", "size": [2.4, 0.75, 1.0],
         "position": [0, 0, 0]},
        {"id": "prop_bench", "name": "长凳", "kind": "bench", "size": [2.0, 0.45, 0.4],
         "position": [0, 0, -1.6]},
        {"id": "prop_wall", "name": "北墙", "kind": "box", "size": [6.0, 3.0, 0.2],
         "position": [0, 0, -3.0], "semanticType": "wall"},
    ],
    "camera": {"shot": "平视中景", "lensMm": 48, "fov": 48,
               "position": [3.2, 1.6, 3.4], "target": [0, 1.1, 0],
               "movement": "缓慢推近", "aspectRatio": "16:9"},
    "lighting": {"key": "左后方冷色主光", "fill": "右前方弱补光", "mood": "紧张"},
    "continuity": ["人物与座位身份不变"],
}

OVERLAY = {
    "version": "1.0",
    "base": "SCENE_LOC_02",
    "shot": "E01_SH01_S01",
    "characters": [
        {"id": "char_lxm", "position": [0, 0, 1.2], "facing": 0.0, "posePreset": "stand"},
        {"id": "char_sw", "position": [0, 0.45, -1.6], "facing": 3.1416,
         "posePreset": "sit"},
    ],
    "camera": {"position": [3.2, 1.6, 3.4], "target": [0, 1.1, 0], "fov": 48},
}


def run_docs(docs):
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, doc in docs.items():
            path = Path(tmp) / name
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            paths.append(path)
        return validator.run(paths)


class SpaceBlockingTest(unittest.TestCase):
    def test_valid_scene_passes(self):
        errors, warnings = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": OVERLAY})
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_facing_mismatch_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["facingTarget"] = [0, 0, 4.2]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("facing" in e for e in errors), errors)

    def test_facing_target_matches_computed_value(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["facingTarget"] = [0, 0, 4.2]
        doc["characters"][0]["facing"] = validator._facing_to_target(
            doc["characters"][0]["position"], [0, 0, 4.2])
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertEqual([e for e in errors if "facing" in e], [])

    def test_standing_not_on_ground_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["position"] = [0, 0.4, 1.2]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("未接地" in e for e in errors), errors)

    def test_sit_without_support_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][1]["position"] = [0, 0.45, 2.4]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("承托面" in e for e in errors), errors)

    def test_tight_clearance_is_warning(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["position"] = [0, 0, 0.6]
        errors, warnings = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertEqual(errors, [])
        self.assertTrue(any("间距" in w for w in warnings), warnings)

    def test_movement_path_through_table_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["movementPath"] = [[0, 0, 2.0], [0, 0, -2.0]]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("movementPath 穿过" in e for e in errors), errors)

    def test_movement_path_off_table_is_clean(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["movementPath"] = [[2.2, 0, 2.0], [2.2, 0, -2.0]]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertEqual([e for e in errors if "movementPath" in e], [])

    def test_undeclared_position_change_between_shots_is_error(self):
        second = json.loads(json.dumps(OVERLAY))
        second["shot"] = "E01_SH01_S02"
        second["characters"][0]["position"] = [0.9, 0, 1.2]
        errors, _ = run_docs({
            "SCENE_LOC_02.json": BASE,
            "E01_SH01_S01.json": OVERLAY,
            "E01_SH01_S02.json": second,
        })
        self.assertTrue(any("未声明 movementPath" in e for e in errors), errors)

    def test_declared_move_between_shots_is_clean(self):
        second = json.loads(json.dumps(OVERLAY))
        second["shot"] = "E01_SH01_S02"
        second["characters"][0]["position"] = [0.9, 0, 1.2]
        second["characters"][0]["movementPath"] = [[0, 0, 1.2], [0.9, 0, 1.2]]
        errors, _ = run_docs({
            "SCENE_LOC_02.json": BASE,
            "E01_SH01_S01.json": OVERLAY,
            "E01_SH01_S02.json": second,
        })
        self.assertEqual([e for e in errors if "movementPath" in e], [])

    def test_missing_base_reference_is_error(self):
        errors, _ = run_docs({"E01_SH01_S01.json": OVERLAY})
        self.assertTrue(any("不存在的基础场景" in e for e in errors), errors)

    def test_unknown_character_id_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"].append({"id": "char_x", "position": [1, 0, 0],
                                  "facing": 0.0, "posePreset": "stand"})
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("不在基底场景中" in e for e in errors), errors)

    def test_old_weapon_id_is_error(self):
        base = json.loads(json.dumps(BASE))
        base["characters"][0]["weapon"] = "sword"
        errors, _ = run_docs({"SCENE_LOC_02.json": base})
        self.assertTrue(any("旧武器 ID" in e for e in errors), errors)

    def test_camera_inside_prop_volume_is_error(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["camera"]["position"] = [0, 0.4, 0]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertTrue(any("camera 位于道具" in e for e in errors), errors)

    def test_camera_above_prop_is_clean(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["camera"]["position"] = [0, 1.2, 0]
        errors, _ = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertEqual([e for e in errors if "camera" in e], [])

    def test_overhead_roof_does_not_block_exit_path(self):
        """车顶/顶棚在头顶：人物从车内下车必然从其正投影下方穿过，不算穿模。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "prop_roof", "name": "车顶", "kind": "wall",
                              "size": [1.95, 0.08, 4.6], "position": [0, 1.72, 0]})
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[0, 0, 0.8], [0, 0, -0.8]]
        errors, _ = run_docs({"SCENE_LOC_02.json": base, "ovl.json": overlay})
        self.assertFalse(any("穿过道具 prop_roof" in e for e in errors), errors)

    def test_low_car_roof_is_overhead_too(self):
        """车内顶棚 y=1.30、厚 0.06：坐姿通过时仍在头顶之上，不算穿模。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "prop_roof_low", "name": "车内顶棚", "kind": "wall",
                              "size": [1.95, 0.06, 4.6], "position": [0, 1.30, 0]})
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[0, 0.45, 0.8], [0, 0.45, -0.8]]
        errors, _ = run_docs({"SCENE_LOC_02.json": base, "ovl.json": overlay})
        self.assertFalse(any("prop_roof_low" in e for e in errors), errors)

    def test_thick_low_beam_still_blocks(self):
        """低矮但厚的横梁（y=1.30、厚 0.4）不是顶棚，仍然要拦。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "prop_beam", "name": "横梁", "kind": "box",
                              "size": [1.95, 0.40, 0.4], "position": [0, 1.30, 0]})
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[0, 0.45, 0.8], [0, 0.45, -0.8]]
        errors, _ = run_docs({"SCENE_LOC_02.json": base, "ovl.json": overlay})
        self.assertTrue(any("prop_beam" in e for e in errors), errors)

    def test_ground_wall_still_blocks_path(self):
        """有厚度的地面墙仍然拦动线（别把上一条放宽成「什么都穿过」）。"""
        import copy
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[0, 0, 1.2], [0, 0, -3.0]]
        errors, _ = run_docs({"SCENE_LOC_02.json": copy.deepcopy(BASE), "ovl.json": overlay})
        self.assertTrue(any("穿过道具 prop_wall" in e for e in errors), errors)

    def test_held_prop_is_not_a_static_obstacle(self):
        """手持道具随持有人移动：旁人贴近它不算撞到实体。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "PROP_05", "name": "字条", "kind": "box",
                              "size": [0.12, 0.12, 0.12], "position": [0.2, 1.18, 1.2],
                              "heldBy": "char_sw"})
        errors, warnings = run_docs({"SCENE_LOC_02.json": base, "ovl.json": copy.deepcopy(OVERLAY)})
        self.assertFalse(any("PROP_05" in e for e in errors), errors)
        self.assertFalse(any("PROP_05" in w for w in warnings), warnings)

    def test_boarding_path_into_vehicle_is_clean(self):
        """上车：动线端点落在车舱内，不算穿过车体（经车门）。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "prop_car", "name": "越野车", "kind": "vehicle",
                              "size": [2.1, 0.72, 5.8], "position": [0, 0, 0],
                              "semanticType": "vehicle"})
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[0, 0, 3.4], [0, 0.45, -0.55]]
        overlay["characters"][0]["posePreset"] = "sit"
        overlay["characters"][0]["position"] = [0, 0.45, -0.55]
        errors, _ = run_docs({"SCENE_LOC_02.json": base, "ovl.json": overlay})
        self.assertFalse(any("prop_car" in e for e in errors), errors)

    def test_walking_through_vehicle_side_is_error(self):
        """绕行穿车：两个端点都在车外，仍判穿模。"""
        import copy
        base = copy.deepcopy(BASE)
        base["props"].append({"id": "prop_car", "name": "越野车", "kind": "vehicle",
                              "size": [2.1, 0.72, 5.8], "position": [0, 0, 6.0],
                              "semanticType": "vehicle"})
        overlay = copy.deepcopy(OVERLAY)
        overlay["characters"][0]["movementPath"] = [[-2.2, 0, 6.0], [2.2, 0, 6.0]]
        errors, _ = run_docs({"SCENE_LOC_02.json": base, "ovl.json": overlay})
        self.assertTrue(any("prop_car" in e for e in errors), errors)

    def test_served_seat_exempts_clearance_and_path(self):
        base = json.loads(json.dumps(BASE))
        base["props"][1]["serves"] = ["char_sw"]
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][1]["position"] = [0, 0.45, -1.6]
        doc["characters"][1]["movementPath"] = [[0, 0.45, -1.6], [2.2, 0, -1.6]]
        errors, warnings = run_docs({"SCENE_LOC_02.json": base, "E01_SH01_S01.json": doc})
        self.assertEqual([e for e in errors if "movementPath" in e], [])
        self.assertEqual([w for w in warnings if "间距" in w], [])

    def test_declared_contact_exempts_clearance(self):
        doc = json.loads(json.dumps(OVERLAY))
        doc["characters"][0]["position"] = [0, 0, 0.6]
        doc["characters"][0]["touching"] = ["prop_table"]
        errors, warnings = run_docs({"SCENE_LOC_02.json": BASE, "E01_SH01_S01.json": doc})
        self.assertEqual(errors, [])
        self.assertEqual([w for w in warnings if "间距" in w], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
