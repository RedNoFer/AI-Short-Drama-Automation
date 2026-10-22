#!/usr/bin/env python3
"""validate_stage_artifacts.py（阶段出口门）的回归自测。

运行：python3 scripts/tests/test_stage_gates.py

本测试对应 PROC-05 事故：阶段 2/3 的站位层整段被跳过，而流水线上没有任何一道门
会因为它缺席而失败。以下用例把「该拦」与「不该误拦」两侧都钉住。

关键纪律：
  · 必须有一条用例证明「风险场景缺基底 = 判错」；
  · 必须有一条用例证明「输入单登记豁免后放行」；
  · 必须有一条用例证明「数据库为空的目录不会静默通过」；
  · 必须有一条用例证明「别的项目命名（非 0X- 模板）不误报」。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stage_gates", ROOT / "scripts" / "validate_stage_artifacts.py")
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)

ROLES = """### 角色 CHAR_01｜阿泽（领队）

### 角色 CHAR_02｜苏晚（观察者）
"""


def build(workdir: Path, *, input_extra: str = "", assets: str = "", script: str = None,
          bases: dict | None = None, overlays: dict | None = None,
          shards: dict | None = None, inheritance: bool = False) -> Path:
    internal = workdir / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(f"# 项目输入单\n\n{input_extra}\n", encoding="utf-8")
    (internal / "01-故事档案与分集规划.md").write_text("# 分集规划\n", encoding="utf-8")
    (internal / "02-逐集拍摄剧本.md").write_text(
        script if script is not None else "# 剧本\n\n### 场景 LOC_01｜公路\n阿泽：走。\n苏晚：好。\n", encoding="utf-8")
    (internal / "03-资产与空间设计.md").write_text(
        ROLES + "\n" + assets, encoding="utf-8")
    space = internal / "04b-站位图"
    if bases:
        space.mkdir(parents=True, exist_ok=True)
        for name, doc in bases.items():
            (space / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if overlays:
        space.mkdir(parents=True, exist_ok=True)
        for name, doc in overlays.items():
            (space / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if inheritance:
        (space / "站位继承表.md").write_text("| 镜 | 站位 |\n", encoding="utf-8")
    if shards is not None:
        shard_dir = internal / "分镜编译"
        shard_dir.mkdir(parents=True, exist_ok=True)
        for name, text in shards.items():
            (shard_dir / f"{name}.md").write_text(text, encoding="utf-8")
    return workdir


BASE_DOC = {
    "version": "1.0",
    "scene": {"name": "公路", "environment": "户外公路"},
    "characters": [{"id": "char_aze", "name": "阿泽", "position": [0, 0, 0], "facing": 0.0}],
    "props": [],
    "camera": {"position": [0, 1, -5], "target": [0, 1, 0], "fov": 60},
    "lighting": {"key": "晨光"},
    "continuity": {"grid": "x"},
}

OVERLAY_DOC = {
    "version": "1.0",
    "base": "SCENE_LOC_01",
    "shot": "E01_SH01_S02",
    "timecode": "2-5",
    "characters": [{"id": "char_aze", "name": "阿泽", "inFrame": True}],
    "camera": {"position": [0, 1, -5], "target": [0, 1, 0], "fov": 60},
}

SHARD = """# E01

| 拍 | 内容 |

本文含 视感自查 上下文衔接自查 群像自检 持物链承接 四张表。
"""

ASSETS_OK = "## 声线母版\n\n## 角色美工账\n\n## 持物链\n\n"


class StageGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ---------- 该拦 ----------
    def test_missing_stage2_base_is_error(self):
        """风险场景（剧本里 ≥2 人同场）缺场景基底 → 判错（PROC-05 的核心用例）。"""
        build(self.workdir, assets=ASSETS_OK)
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("场景基底" in e for e in errors), errors)

    def test_missing_holdings_chain_is_error(self):
        """资产类文件缺持物链 → 判错（防「道具早于获取点出现」）。"""
        build(self.workdir, assets="## 声线母版\n\n## 角色美工账\n\n",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("持物链" in e for e in errors), errors)

    def test_missing_voice_master_is_error(self):
        build(self.workdir, assets="## 角色美工账\n\n## 持物链\n\n",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("声线母版" in e for e in errors), errors)

    def test_stage3_missing_overlays_is_error(self):
        """逐镜表命中风险镜头但无任何 overlay → 判错。"""
        build(self.workdir, assets=ASSETS_OK, bases={"SCENE_LOC_01": BASE_DOC},
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors, _ = gates.stage3(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("镜级增量" in e for e in errors), errors)

    def test_stage3_missing_inheritance_table_is_error(self):
        build(self.workdir, assets=ASSETS_OK, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC},
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors, _ = gates.stage3(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("站位继承表" in e for e in errors), errors)

    def test_stage4_missing_space_dir_is_error(self):
        """交付包命中风险闸门、但站位目录不存在 → 判错，不静默通过。"""
        build(self.workdir, assets=ASSETS_OK)
        (self.workdir / "精简制作包.md").write_text(
            "# 包\n\n2-5秒，硬切，阿泽看向苏晚。\n", encoding="utf-8")
        errors, _ = gates.stage4(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("站位层" in e for e in errors), errors)

    def test_base_missing_required_field_is_error(self):
        broken = {k: v for k, v in BASE_DOC.items() if k != "camera"}
        build(self.workdir, assets=ASSETS_OK, bases={"SCENE_LOC_01": broken})
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("缺字段 camera" in e for e in errors), errors)

    # ---------- 不该误拦 ----------
    def test_complete_project_passes(self):
        build(self.workdir, assets=ASSETS_OK, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC}, inheritance=True,
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        (self.workdir / "精简制作包.md").write_text(
            "# 包\n\n2-5秒，硬切，阿泽看向苏晚。\n", encoding="utf-8")
        for stage in ("2", "3", "4"):
            errors, warnings = {"2": gates.stage2, "3": gates.stage3, "4": gates.stage4}[stage](
                self.workdir, ["阿泽", "苏晚"])
            self.assertEqual(errors, [], f"阶段{stage} 误报：{errors}")

    def test_exemption_in_brief_passes(self):
        """输入单登记「站位层：豁免」后放行（留痕式跳过，而非默认跳过）。"""
        build(self.workdir, assets=ASSETS_OK,
              input_extra="站位层：豁免（理由：全片单人独白，无同框）",
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors2, warns2 = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        errors3, warns3 = gates.stage3(self.workdir, ["阿泽", "苏晚"])
        self.assertEqual(errors2, [], errors2)
        self.assertEqual(errors3, [], errors3)
        self.assertTrue(any("豁免" in w for w in warns2 + warns3))

    def test_template_naming_variants_pass(self):
        """别的项目用不同命名（01-剧本蓝图 / 02-资产卡）也不误报。"""
        internal = self.workdir / "内部"
        internal.mkdir(parents=True)
        (internal / "00-项目输入单.md").write_text("# 输入单\n", encoding="utf-8")
        (internal / "01-剧本蓝图.md").write_text("# 蓝图\n", encoding="utf-8")
        (internal / "02-资产卡.md").write_text(
            ROLES + "\n## 声线母版\n## 角色美工账\n## 持物链\n", encoding="utf-8")
        (internal / "04b-站位图").mkdir()
        (internal / "04b-站位图" / "SCENE_LOC_01.json").write_text(
            json.dumps(BASE_DOC, ensure_ascii=False), encoding="utf-8")
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertEqual(errors, [], errors)

    def test_stage_exemption_requires_reason(self):
        """写了「阶段门豁免：持物链（理由：…）」才放行；不写理由视为无效。"""
        build(self.workdir, assets="## 声线母版\n\n## 角色美工账\n\n",
              input_extra="阶段门豁免：持物链（理由：旧版重制，道具链已在分镜承接行逐段登记）",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, warnings = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("持物链" in w and "豁免" in w for w in warnings), warnings)

    def test_stage_exemption_without_reason_is_ignored(self):
        build(self.workdir, assets="## 声线母版\n\n## 角色美工账\n\n",
              input_extra="阶段门豁免：持物链",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, ["阿泽", "苏晚"])
        self.assertTrue(any("持物链" in e for e in errors), errors)

    def test_single_character_project_needs_no_space_layer(self):
        """全程单人/空镜的项目不触发风险闸门，不要求站位层。"""
        build(self.workdir, assets=ASSETS_OK,
              script="# 剧本\n\n### 场景 LOC_01｜荒野\n阿泽：走。\n",
              shards={"E01": SHARD + "\n0-5秒，空镜，风穿过碎石。\n"})
        (self.workdir / "精简制作包.md").write_text("# 包\n\n0-5秒，空镜，风穿过碎石。\n", encoding="utf-8")
        for fn in (gates.stage2, gates.stage3, gates.stage4):
            errors, _ = fn(self.workdir, ["阿泽", "苏晚"])
            self.assertEqual(errors, [], errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
