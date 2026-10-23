#!/usr/bin/env python3
"""站位—正文交叉校验的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_space_sync.py
覆盖 validate_compact_package.py 的 check_space_sync：增量数、时间码、
坐标泄漏、画内未绑定、左右侧矛盾，以及无站位层时的跳过行为。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))

HEADER = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
```
"""

ROWS = "\n".join([
    '0-5秒，阿泽站在雨里，镜头平视不动，他作口型对白、口型同步，说："你好。"',
    '5-10秒，硬切，风吹过路面，他侧头听声。',
    '10-15秒，硬切，远处雾里有光，他向前一步。',
    '15-20秒，硬切，他停住脚步，眉头收紧。',
    '20-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
])

LOCK = "声线锁定：CHAR_01 阿泽＝26岁男声，中低音清冷略沙。"

PACKAGE = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 角色 CHAR_02｜配角

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
```

## 剧集 E01｜测试集1

### 小说原文

```text
第1集的小说原文。
```

### 片段 SH01｜30秒｜测试片段

角色：CHAR_01
场景：LOC_01

#### 视频提示词

```text
【参考】CHAR_01=阿泽外观锁定；LOC_01=起点路段。
【公共总规范】统一3D国漫画风。{lock}
【时间轴】
{rows}
【收尾】阿泽走远，下一片段承接。
```
""".format(lock=LOCK, rows=ROWS)


def overlay(index: int, timecode: str, *, x: float = 0.0, in_frame: bool = True,
            name: str = "阿泽", shot: str | None = None, extra: list[dict] | None = None) -> dict:
    characters = [{
        "id": "char_aze", "name": name, "position": [x, 0, 0],
        "facing": 0.0, "posePreset": "stand", "inFrame": in_frame,
    }]
    characters.extend(extra or [])
    return {
        "version": "1.0",
        "base": "SCENE_LOC_01",
        "shot": shot or f"E01_SH01_S{index:02d}",
        "timecode": timecode,
        "characters": characters,
        "camera": {"position": [0, 1.5, 6.0], "target": [0, 1.0, 0], "fov": 40},
    }


def space_files(overlays: list[dict]) -> dict:
    return {o["shot"] + ".json": o for o in overlays}


def run(overlays: list[dict] | None, package: str = PACKAGE) -> tuple[list, list, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        space_dir = root / "内部" / "04b-站位图"
        space_dir.mkdir(parents=True)
        for name, doc in space_files(overlays or []).items():
            (space_dir / name).write_text(json.dumps(doc, ensure_ascii=False),
                                          encoding="utf-8")
        result = validator.validate(package, POLICY, space_dir=space_dir)
        return result["errors"], result["warnings"], result["space"]


def default_overlays() -> list[dict]:
    codes = [("0-5", 0.0), ("5-10", 0.0), ("10-15", 0.0),
             ("15-20", 0.0), ("20-25", 0.0), ("25-30", 0.0)]
    return [overlay(i + 1, code, x=x) for i, (code, x) in enumerate(codes)]


class SpaceSyncTest(unittest.TestCase):
    def test_matching_overlays_pass(self):
        errors, warnings, stats = run(default_overlays())
        self.assertEqual([e for e in errors if "站位" in e or "画内" in e], [])
        self.assertEqual(stats["status"], "checked")
        self.assertEqual(stats["fragments"], 1)
        self.assertEqual(stats["overlays"], 6)

    RISKY = PACKAGE.replace(
        "5-10秒，硬切，风吹过路面，他侧头听声。",
        "5-10秒，硬切，阿泽与配角并肩站着，风从两人之间穿过去。")

    def test_missing_space_dir_with_risk_shots_is_error(self):
        """命中风险闸门却缺站位层 → 判错（PROC-05：跳过它曾经是零成本）。"""
        result = validator.validate(self.RISKY, POLICY, space_dir=Path("/nonexistent"))
        self.assertEqual(result["space"]["status"], "skipped")
        self.assertGreater(result["space"]["risk_shots"], 0)
        self.assertTrue(any("站位层缺失" in e for e in result["errors"]), result["errors"])

    def test_single_character_package_needs_no_space_layer(self):
        """全程单人的包不触发风险闸门，缺站位层不判错。"""
        result = validator.validate(PACKAGE, POLICY, space_dir=Path("/nonexistent"))
        self.assertEqual(result["space"]["risk_shots"], 0)
        self.assertFalse(any("站位层缺失" in e for e in result["errors"]), result["errors"])

    def test_missing_space_dir_with_exemption_passes(self):
        """输入单登记豁免后放行，并留一条提醒。"""
        result = validator.validate(PACKAGE, POLICY, space_dir=Path("/nonexistent"),
                                    space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(any("豁免" in w for w in result["warnings"]), result["warnings"])

    def test_partial_coverage_is_allowed(self):
        """W18 只要求命中闸门的镜头写 overlay，部分覆盖合法。"""
        errors, _, _ = run(default_overlays()[:4])
        self.assertFalse(any("与正文镜头" in e for e in errors), errors)

    def test_overlay_pointing_past_last_shot_is_error(self):
        """overlay 的 shot 编号指向不存在的镜头 → 判错。"""
        overlays = default_overlays()[:2]
        overlays.append(overlay(99, "0-5"))
        errors, _, _ = run(overlays)
        self.assertTrue(any("存在的镜头之外" in e for e in errors), errors)

    def test_metaphorical_coordinate_is_not_leak(self):
        """「仪表微光成了唯一的坐标」是比喻，不是站位 JSON 泄漏。"""
        pkg = PACKAGE.replace("他停住脚步", "仪表微光成了唯一的坐标，他停住脚步")
        errors, _, _ = run(default_overlays(), package=pkg)
        self.assertFalse(any("坐标" in e for e in errors), errors)

    def test_coordinate_numbers_are_leak(self):
        """正文写出坐标数值 → 判泄漏。"""
        pkg = PACKAGE.replace("他停住脚步", "坐标：[0.5, 0, 1.2]，他停住脚步")
        errors, _, _ = run(default_overlays(), package=pkg)
        self.assertTrue(any("站位 JSON 内部写法" in e for e in errors), errors)

    def test_timecode_mismatch_is_error(self):
        overlays = default_overlays()
        overlays[2]["timecode"] = "11-15"
        errors, _, _ = run(overlays)
        self.assertTrue(any("时间码" in e for e in errors), errors)

    def test_coordinate_leak_is_error(self):
        package = PACKAGE.replace("【收尾】", "position=[0, 0, 1.2]\n【收尾】")
        errors, _, _ = run(default_overlays(), package)
        self.assertTrue(any("站位 JSON 内部写法" in e for e in errors), errors)

    def test_in_frame_character_not_bound_is_error(self):
        overlays = default_overlays()
        overlays[0]["characters"].append({
            "id": "char_side", "name": "配角", "position": [3, 0, 0],
            "facing": 0.0, "posePreset": "stand", "inFrame": True,
        })
        errors, _, _ = run(overlays)
        self.assertTrue(any("未绑定" in e for e in errors), errors)

    def test_offscreen_character_not_bound_is_fine(self):
        overlays = default_overlays()
        overlays[0]["characters"].append({
            "id": "char_side", "name": "配角", "position": [3, 0, 0],
            "facing": 0.0, "posePreset": "stand", "inFrame": False,
        })
        errors, _, _ = run(overlays)
        self.assertEqual([e for e in errors if "未绑定" in e], [])

    def test_side_contradiction_is_warning(self):
        overlays = default_overlays()
        overlays[0]["characters"][0]["position"] = [2.0, 0, 0]
        package = PACKAGE.replace("阿泽站在雨里", "阿泽站在画面左侧的雨里")
        errors, warnings, _ = run(overlays, package)
        self.assertTrue(any("侧" in w for w in warnings), warnings)
        self.assertEqual(errors, [])

    def test_unknown_in_frame_name_is_warning(self):
        overlays = default_overlays()
        overlays[0]["characters"][0]["name"] = "陌生角色"
        errors, warnings, _ = run(overlays)
        self.assertTrue(any("没有同名角色资产" in w for w in warnings), warnings)
        self.assertEqual([e for e in errors if "画内" in e], [])

    def test_in_frame_character_absent_from_body_is_warning(self):
        overlays = default_overlays()
        overlays[0]["characters"].append({
            "id": "char_side", "name": "配角", "position": [3, 0, 0],
            "facing": 0.0, "posePreset": "stand", "inFrame": True,
        })
        package = PACKAGE.replace("角色：CHAR_01\n", "角色：CHAR_01,CHAR_02\n")
        errors, warnings, _ = run(overlays, package)
        self.assertEqual([e for e in errors if "未绑定" in e], [])
        self.assertTrue(any("正文没有提到" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
