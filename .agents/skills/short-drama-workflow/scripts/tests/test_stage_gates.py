#!/usr/bin/env python3
"""validate_stage_artifacts.py（阶段出口门）的回归自测。

运行：python3 scripts/tests/test_stage_gates.py

本测试覆盖两轮事故：
  · PROC-05（2026-10-22）：阶段 2/3 的站位层整段被跳过，而流水线上没有任何一道门
    会因为它缺席而失败。
  · 审计缺口（2026-10-23）：阶段 2/3 的「必登内容」只查关键字，写个空标题、
    贴张空表格就能过门；阶段 3.5 打斗路由完全没有门；阶段 2 没有独立评审。

关键纪律：
  · 必须有用例证明「风险场景缺基底 = 判错」；
  · 必须有用例证明「输入单登记豁免后放行」；
  · 必须有用例证明「空标题 / 空表格 = 判错」（不能靠关键字过门）；
  · 必须有用例证明「声明值与逐镜表不一致 = 判错」；
  · 必须有用例证明「别的项目命名（非 0X- 模板）不误报」。
"""

from __future__ import annotations

import importlib.util
import json
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

ASSETS_OK = """## 声线母版

| 角色 | 音色锚点 | 反差设计 |
|---|---|---|
| 阿泽 | 低沉、语速慢、尾音下压 | 与苏晚清亮形成反差 |
| 苏晚 | 清亮、语速快、尾音上扬 | 与阿泽低沉形成反差 |

## 角色美工账

| 角色 | 脸型与眉眼鼻唇 | 妆造 | 发型发饰 | 饰件 | 服装三层 |
|---|---|---|---|---|---|
| 阿泽 | 窄长脸，眉骨高，鼻梁直，唇薄 | 素颜，不施妆 | 短发，无发饰 | 无饰品 | 冲锋衣，哑光尼龙 |
| 苏晚 | 方圆脸，眼圆，鼻尖圆，唇厚 | 薄妆，眼线细 | 长发低马尾 | 银耳钉 | 棉质外套 |

## 持物链

| 道具 | 获取点 | 持有人变更 | 去向 |
|---|---|---|---|
| PROP_01 古图 | E01-SH01 包裹拆出 | 阿泽→苏晚 E03 | 终场留在车内 |
"""

REVIEW_OK = """# 阶段 2 资产独立评审（评稿人：子任务 R-03）

- 身份锚点：两个角色的脸型、眉眼鼻唇相对关系、发饰背面衔接逐项复核，均可在正侧背三视图成立。
- 角色美工账：两行齐全，妆造版本与饰件清单无「留空」。
- 声线母版：锚点 3–5 个，阿泽与苏晚盲听可辨人，旁白与混叠人声已单独定义。
- 持物链：古图获取点晚于首次出场镜头，无「道具早于获取点出现」。
- 结论：通过，无阻断项。
"""

ROUTING_OK = """# 打斗路由判定表

| 片段 | 等级 | 原文证据 |
|---|---|---|
| E01-SH01 | C | 纯叙述开场，无冲突 |
| E01-SH02 | B | 有推搡，属混合段 |
"""

SHOT_TABLE = """### 视感自查

视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；机位角度种数=6；侧45占比=33.3%

| 镜 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 固定 |
|---|---|---|---|---|---|---|
| S01 | 大远景 | 24mm | 正面平视 | 极缓慢横移 | 深 | 否 |
| S02 | 全景 | 35mm | 侧45平视 | 极缓慢横移 | 深 | 否 |
| S03 | 中景 | 50mm | 侧45微俯 | 手持微晃跟拍 | 浅 | 否 |
| S04 | 中近景 | 85mm | 侧面90平视 | 极缓推镜 | 浅 | 否 |
| S05 | 特写 | 50mm | 侧背平视 | 极缓推镜 | 浅 | 否 |
| S06 | 全景 | 35mm | 背面平视 | 缓慢拉镜 | 深 | 否 |

### 上下文衔接自查

| 镜对 | 站位朝向 | 道具链 | 情绪话头 |
|---|---|---|---|
| S01↔S02 | 阿泽原地，苏晚后退半步 | 无持物→无持物 | 沉默→沉默 |

### 群像自检

| 片段 | 画内人数 | 人数锁定句 |
|---|---|---|
| E01/SH01 | 2 | 本镜画面内恰好两人 |

### 持物链承接

| 片段 | 入口持物 | 出口持物 |
|---|---|---|
| E01/SH01 | 无 | 包裹在阿泽手里 |
"""

SHARD = "# E01\n\n" + SHOT_TABLE


def build(workdir: Path, *, input_extra: str = "", assets: str = None, script: str = None,
          bases: dict | None = None, overlays: dict | None = None,
          shards: dict | None = None, inheritance: bool = False,
          review: bool = True, routing: bool = True) -> Path:
    internal = workdir / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(f"# 项目输入单\n\n{input_extra}\n", encoding="utf-8")
    (internal / "01-故事档案与分集规划.md").write_text("# 分集规划\n", encoding="utf-8")
    (internal / "02-逐集拍摄剧本.md").write_text(
        script if script is not None else "# 剧本\n\n### 场景 LOC_01｜公路\n阿泽：走。\n苏晚：好。\n", encoding="utf-8")
    (internal / "03-资产与空间设计.md").write_text(
        ROLES + "\n" + (ASSETS_OK if assets is None else assets), encoding="utf-8")
    if review:
        (internal / "03b-资产评审.md").write_text(REVIEW_OK, encoding="utf-8")
    if routing:
        (internal / "04b-打斗路由判定表.md").write_text(ROUTING_OK, encoding="utf-8")
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

NAMES = ["阿泽", "苏晚"]


class StageGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ---------- 该拦：站位层（PROC-05） ----------
    def test_missing_stage2_base_is_error(self):
        """风险场景（剧本里 ≥2 人同场）缺场景基底 → 判错（PROC-05 的核心用例）。"""
        build(self.workdir)
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("场景基底" in e for e in errors), errors)

    def test_stage3_missing_overlays_is_error(self):
        """逐镜表命中风险镜头但无任何 overlay → 判错。"""
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors, _ = gates.stage3(self.workdir, NAMES)
        self.assertTrue(any("镜级增量" in e for e in errors), errors)

    def test_stage3_missing_inheritance_table_is_error(self):
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC},
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors, _ = gates.stage3(self.workdir, NAMES)
        self.assertTrue(any("站位继承表" in e for e in errors), errors)

    def test_stage4_missing_space_dir_is_error(self):
        """交付包命中风险闸门、但站位目录不存在 → 判错，不静默通过。"""
        build(self.workdir)
        (self.workdir / "精简制作包.md").write_text(
            "# 包\n\n2-5秒，硬切，阿泽看向苏晚。\n", encoding="utf-8")
        errors, _ = gates.stage4(self.workdir, NAMES)
        self.assertTrue(any("站位层" in e for e in errors), errors)

    def test_base_missing_required_field_is_error(self):
        broken = {k: v for k, v in BASE_DOC.items() if k != "camera"}
        build(self.workdir, bases={"SCENE_LOC_01": broken})
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("缺字段 camera" in e for e in errors), errors)

    # ---------- 该拦：空标题/空表格（2026-10-23 审计缺口） ----------
    def test_empty_voice_master_is_error(self):
        """只写标题不写内容 → 判错（原来关键字命中即放行）。"""
        assets = ASSETS_OK.replace(
            "| 阿泽 | 低沉、语速慢、尾音下压 | 与苏晚清亮形成反差 |\n"
            "| 苏晚 | 清亮、语速快、尾音上扬 | 与阿泽低沉形成反差 |\n", "")
        build(self.workdir, assets=assets, bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("声线母版" in e and "空标题" in e for e in errors), errors)

    def test_art_ledger_missing_character_row_is_error(self):
        """角色只写在提示词里、美工账上没有行 → 判错（未定版）。"""
        assets = ASSETS_OK.replace("| 苏晚 | 方圆脸，眼圆，鼻尖圆，唇厚 | 薄妆，眼线细 | 长发低马尾 | 银耳钉 | 棉质外套 |\n", "")
        build(self.workdir, assets=assets, bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("美工账缺这些角色" in e and "苏晚" in e for e in errors), errors)

    def test_missing_stage2_review_is_error(self):
        """阶段 2 没有独立评审记录 → 判错（资产母版不能只靠自检）。"""
        build(self.workdir, review=False, bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("03b-资产评审" in e for e in errors), errors)

    def test_empty_context_check_table_is_error(self):
        """上下文衔接自查只留表头、无数据行 → 判错。"""
        shard = SHARD.replace(
            "| S01↔S02 | 阿泽原地，苏晚后退半步 | 无持物→无持物 | 沉默→沉默 |\n", "")
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC}, inheritance=True,
              shards={"E01": shard})
        errors, _ = gates.stage3(self.workdir, NAMES)
        self.assertTrue(any("上下文衔接" in e and "行数据" in e for e in errors), errors)

    def test_stats_mismatch_is_error(self):
        """视感统计声明值与逐镜表实算值不一致 → 判错。"""
        shard = SHARD.replace("镜数=6", "镜数=8")
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC}, inheritance=True,
              shards={"E01": shard})
        errors, _ = gates.stage3(self.workdir, NAMES)
        self.assertTrue(any("镜数" in e and "实算 6" in e for e in errors), errors)

    def test_missing_shot_table_is_error(self):
        """视感自查退化成散文、没有可校验的逐镜表 → 判错。"""
        shard = SHARD.split("### 上下文衔接自查")[0].replace(
            "| 镜 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 固定 |", "| 说明 |")
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC}, inheritance=True,
              shards={"E01": shard + "\n### 上下文衔接自查\n\n| 镜对 | 站位 | 道具 | 情绪 |\n|---|---|---|---|\n| S01↔S02 | 原地 | 无 | 沉默 |\n"
                      "\n### 群像自检\n\n| 片段 | 画内人数 |\n|---|---|\n| E01 | 2 |\n"
                      "\n### 持物链承接\n\n| 片段 | 入口 | 出口 |\n|---|---|---|\n| E01 | 无 | 包裹 |\n"})
        errors, _ = gates.stage3(self.workdir, NAMES)
        self.assertTrue(any("逐镜表" in e for e in errors), errors)

    # ---------- 该拦：阶段 3.5 打斗路由 ----------
    def test_missing_routing_table_is_error(self):
        build(self.workdir, routing=False, bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage35(self.workdir, NAMES)
        self.assertTrue(any("打斗路由判定表" in e for e in errors), errors)

    def test_grade_a_without_beat_table_is_error(self):
        """A 级一镜到底会豁免硬切与镜数带，必须有拍点表与证据。"""
        internal = self.workdir / "内部"
        internal.mkdir(parents=True, exist_ok=True)
        (internal / "04b-打斗路由判定表.md").write_text(
            "# 打斗路由\n\n| 片段 | 等级 | 说明 |\n|---|---|---|\n| E01-SH01 | A | 全打斗段 |\n",
            encoding="utf-8")
        errors, _ = gates.stage35(self.workdir, NAMES)
        self.assertTrue(any("拍点" in e for e in errors), errors)

    def test_no_fight_declaration_passes(self):
        """全剧无打斗时写一行声明即可，不强制造表。"""
        internal = self.workdir / "内部"
        internal.mkdir(parents=True, exist_ok=True)
        (internal / "04b-打斗路由判定表.md").write_text(
            "# 打斗路由判定\n\n全剧无打斗段，逐片段均为 C（证据：全剧仅对白与走位，无肢体冲突）。\n",
            encoding="utf-8")
        errors, warnings = gates.stage35(self.workdir, NAMES)
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("均为 C" in w for w in warnings), warnings)

    # ---------- 不该误拦 ----------
    def test_complete_project_passes(self):
        build(self.workdir, bases={"SCENE_LOC_01": BASE_DOC},
              overlays={"E01_SH01_S02": OVERLAY_DOC}, inheritance=True,
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        (self.workdir / "精简制作包.md").write_text(
            "# 包\n\n2-5秒，硬切，阿泽看向苏晚。\n", encoding="utf-8")
        for stage, fn in (("2", gates.stage2), ("3", gates.stage3),
                          ("3.5", gates.stage35), ("4", gates.stage4)):
            errors, _ = fn(self.workdir, NAMES)
            self.assertEqual(errors, [], f"阶段{stage} 误报：{errors}")

    def test_exemption_in_brief_passes(self):
        """输入单登记「站位层：豁免」后放行（留痕式跳过，而非默认跳过）。"""
        build(self.workdir, input_extra="站位层：豁免（理由：全片单人独白，无同框）",
              shards={"E01": SHARD + "\n2-5秒，硬切，阿泽与苏晚并肩。\n"})
        errors2, warns2 = gates.stage2(self.workdir, NAMES)
        errors3, warns3 = gates.stage3(self.workdir, NAMES)
        self.assertEqual(errors2, [], errors2)
        self.assertEqual(errors3, [], errors3)
        self.assertTrue(any("豁免" in w for w in warns2 + warns3))

    def test_template_naming_variants_pass(self):
        """别的项目用不同命名（01-剧本蓝图 / 02-资产卡）也不误报。"""
        internal = self.workdir / "内部"
        internal.mkdir(parents=True)
        (internal / "00-项目输入单.md").write_text("# 输入单\n", encoding="utf-8")
        (internal / "01-剧本蓝图.md").write_text("# 蓝图\n", encoding="utf-8")
        (internal / "02-资产卡.md").write_text(ROLES + "\n" + ASSETS_OK, encoding="utf-8")
        (internal / "03b-资产评审.md").write_text(REVIEW_OK, encoding="utf-8")
        (internal / "04b-站位图").mkdir()
        (internal / "04b-站位图" / "SCENE_LOC_01.json").write_text(
            json.dumps(BASE_DOC, ensure_ascii=False), encoding="utf-8")
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertEqual(errors, [], errors)

    def test_stage_exemption_requires_reason(self):
        """写了「阶段门豁免：持物链（理由：…）」才放行；不写理由视为无效。"""
        assets = ASSETS_OK.replace(
            "## 持物链\n\n| 道具 | 获取点 | 持有人变更 | 去向 |\n|---|---|---|---|\n"
            "| PROP_01 古图 | E01-SH01 包裹拆出 | 阿泽→苏晚 E03 | 终场留在车内 |\n", "")
        build(self.workdir, assets=assets,
              input_extra="阶段门豁免：持物链（理由：旧版重制，道具链已在分镜承接行逐段登记）",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, warnings = gates.stage2(self.workdir, NAMES)
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("持物链" in w and "豁免" in w for w in warnings), warnings)

    def test_stage_exemption_without_reason_is_ignored(self):
        assets = ASSETS_OK.replace(
            "## 持物链\n\n| 道具 | 获取点 | 持有人变更 | 去向 |\n|---|---|---|---|\n"
            "| PROP_01 古图 | E01-SH01 包裹拆出 | 阿泽→苏晚 E03 | 终场留在车内 |\n", "")
        build(self.workdir, assets=assets, input_extra="阶段门豁免：持物链",
              bases={"SCENE_LOC_01": BASE_DOC})
        errors, _ = gates.stage2(self.workdir, NAMES)
        self.assertTrue(any("持物链" in e for e in errors), errors)

    def test_single_character_project_needs_no_space_layer(self):
        """全程单人/空镜的项目不触发风险闸门，不要求站位层。"""
        build(self.workdir, script="# 剧本\n\n### 场景 LOC_01｜荒野\n阿泽：走。\n",
              shards={"E01": SHARD + "\n0-5秒，空镜，风穿过碎石。\n"})
        (self.workdir / "精简制作包.md").write_text("# 包\n\n0-5秒，空镜，风穿过碎石。\n", encoding="utf-8")
        for fn in (gates.stage2, gates.stage3, gates.stage35, gates.stage4):
            errors, _ = fn(self.workdir, NAMES)
            self.assertEqual(errors, [], errors)

    # ---------- 软检查（提醒，不阻断） ----------
    def test_character_field_gaps_are_warnings_not_errors(self):
        """角色九块字段缺口在阶段 2 就报出来，但按 policy 属提醒级。"""
        internal = self.workdir / "内部"
        internal.mkdir(parents=True, exist_ok=True)
        text = "### 角色 CHAR_01｜阿泽\n\n提示词：一个男人站在路上。\n"
        warnings: list[str] = []
        gates._character_field_warnings(text, gates._policy(), warnings)
        self.assertTrue(any("CHAR_01" in w and "缺美工字段" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
