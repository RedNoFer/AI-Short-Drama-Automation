#!/usr/bin/env python3
"""build_handoff.py（派单卡生成器）的回归自测。

运行：python3 scripts/tests/test_build_handoff.py

覆盖：
  · wan30 卡：字符口径仅硬顶18000、无下限、校验命令 --model wan30、绝无 --tier；
  · seedance25 卡：--tier 来自输入单登记档；
  · h3 卡：硬顶 6000、不套 Seedance 档；
  · 生成轨缺失/重复/无效 → 失败关闭（R37）；
  · 上游落盘物缺失 → 失败关闭（PROC-05）；
  · 阶段 4 批次片段不在冻结逐镜表 → 失败关闭；
  · 卡内附规范快照与规则应用清单。
"""

from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_handoff", ROOT / "scripts" / "build_handoff.py")
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)

BRIEF = """# 00 项目输入单

| 项 | 值 |
|---|---|
| 生成轨 | wan30 |
| 覆盖范围 | 全书 |
"""

BRIEF_SEEDANCE = BRIEF.replace("| 生成轨 | wan30 |", "| 生成轨 | seedance25 |\n| 字符档 | tier2_xiaomo63 |")
BRIEF_H3 = BRIEF.replace("wan30", "h3")

TABLE = """# 04 片段规划与逐镜表

## 一、片段 E01-SH01｜开场

| 片段 | 镜 | 起止 | 景别 |
|---|---|---|---|
| SH01 | S01 | 0-3 | 全景 |

## 二、片段 E01-SH02｜转折
"""


def make_project(tmp: Path, brief: str = BRIEF, with_table: bool = True) -> Path:
    internal = tmp / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(brief, encoding="utf-8")
    (internal / "03-资产与空间设计.md").write_text("# 资产\n\n角色 CHAR_01｜阿泽\n", encoding="utf-8")
    (internal / "03a-固定资产图片提示词.md").write_text("# 固定资产图片提示词\n", encoding="utf-8")
    (internal / "02-逐集拍摄剧本.md").write_text("# 剧本\n\n第一场\n", encoding="utf-8")
    (internal / "04a-片段边界.json").write_text(
        json.dumps({"segments": [{"id": "E01-SH01", "dialogue": [], "action_capacity": []}]}),
        encoding="utf-8")
    (internal / "04b-打斗路由判定表.md").write_text("# 打斗路由\n\n本批无打斗。\n", encoding="utf-8")
    if with_table:
        (internal / "04-片段规划与逐镜表.md").write_text(TABLE, encoding="utf-8")
        state = {
            "location": "LOC_01", "time_of_day": "清晨", "light": "窗向自然光",
            "characters": [{"code": "CHAR_01", "pos": "入口", "face": "室内",
                            "costume": "深灰外套", "injury": "无伤"}], "props": [],
        }
        facts = {
            "schema": "continuity-facts/2",
            "upstream": {"file": "04-片段规划与逐镜表.md",
                         "sha256": handoff.wc.sha256_file(internal / "04-片段规划与逐镜表.md")},
            "segments": [
                {"id": "E01-SH01", "shots": [{"no": "S01", "start": 0, "end": 3}],
                 "entry": state, "exit": state, "next": "E01-SH02"},
                {"id": "E01-SH02", "shots": [{"no": "S01", "start": 0, "end": 3}],
                 "entry": state, "exit": state, "next": None},
            ],
        }
        (internal / "04c-衔接事实.json").write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    return tmp


class BuildHandoffTests(unittest.TestCase):
    def test_wan30_card(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            card = handoff.build_card(work, "4", "E01-SH01~SH02")
            self.assertIn("wan30", card)
            self.assertIn("无字数下限", card)
            self.assertIn("硬顶 18000", card)
            self.assertIn("--model wan30", card)
            self.assertNotIn("--tier tier", card)
            self.assertIn("SHA-256", card)
            self.assertIn("规范快照", card)
            self.assertIn("规则应用清单", card)
            self.assertIn("R20", card)
            self.assertIn("audit_wan30_antipatterns.py", card)
            local_audit = next(line for line in card.splitlines() if line.startswith("【Wan本地风险扫描】"))
            self.assertNotIn("--strict", local_audit)
            self.assertIn("--review-record", card)
            self.assertIn("warning登记待独立评审", card)
            self.assertIn("放行前提", card)
            self.assertIn("固定资产图片提示词", card)
            self.assertIn("04a-片段边界.json", card)
            self.assertIn("micro-expression-layer.md", card)
            self.assertIn("人物微表情表演skill.zip#micro-expression-video-generator/references/muscle-dispatch-library.md", card)
            self.assertIn("人物微表情表演skill.zip#micro-expression-video-generator/references/tempo-density-guide.md", card)
            self.assertIn("人物微表情表演skill.zip#micro-expression-video-generator/references/video-prompt-guardrails.md", card)

    def test_seedance_card_has_tier(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF_SEEDANCE)
            card = handoff.build_card(work, "4", "E01-SH01")
            self.assertIn("--tier tier2_xiaomo63", card)
            self.assertIn("≤3000", card)

    def test_wan30_old_brief_length_note_does_not_restore_floor(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF + "\n| 旧字数备注 | 8000–15000 |\n")
            card = handoff.build_card(work, "4", "E01-SH01")
            manifest = handoff.build_manifest(work, "4", "E01-SH01", card)
            self.assertIsNone(manifest["char_budget"]["min_chars"])
            self.assertEqual(manifest["char_budget"]["max_chars"], 18000)
            self.assertIn("无字数下限", card)
            self.assertNotIn("低于 8000 判不通过", card)

    def test_wan30_missing_or_invalid_cap_cannot_fall_back(self):
        policy = handoff.wc.load_policy()
        for cap in (None, 0, -1, True, "18000"):
            with self.subTest(cap=cap):
                profile = json.loads(json.dumps(policy))
                profile["model_profiles"]["wan30"]["prompt_max_chars"] = cap
                with self.assertRaises(ValueError):
                    handoff.load_char_budget(profile, BRIEF, "wan30")

    def test_h3_card(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF_H3)
            card = handoff.build_card(work, "4", "E01-SH01")
            self.assertIn("硬顶 6000", card)
            self.assertIn("--model h3", card)
            self.assertNotIn("--tier tier", card)
            self.assertNotIn("≤3000", card)  # 不套 Seedance 档

    def test_batch_load_guidance_comes_from_selected_branch(self):
        for brief, expected in ((BRIEF, [1, 2]), (BRIEF_SEEDANCE, [2, 4]), (BRIEF_H3, [2, 4])):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d), brief)
                card = handoff.build_card(work, "4", "E01-SH01")
                manifest = handoff.build_manifest(work, "4", "E01-SH01", card)
                self.assertEqual(manifest["recommended_batch_segments"], expected)
                self.assertIn(f"建议每批 {expected[0]}–{expected[1]} 段", card)

    def test_wan_batch_guidance_does_not_override_explicit_range(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            table = work / "内部" / "04-片段规划与逐镜表.md"
            table.write_text(TABLE + "\n## 三、片段 E01-SH03｜收尾\n", encoding="utf-8")
            facts_path = work / "内部" / "04c-衔接事实.json"
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            facts["upstream"]["sha256"] = handoff.wc.sha256_file(table)
            facts["segments"][-1]["next"] = "E01-SH03"
            facts["segments"].append({**facts["segments"][-1], "id": "E01-SH03", "next": None})
            facts_path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
            card = handoff.build_card(work, "4", "E01-SH01~SH03")
            manifest = handoff.build_manifest(work, "4", "E01-SH01~SH03", card)
            self.assertEqual(manifest["segments"], ["E01-SH01", "E01-SH02", "E01-SH03"])
            self.assertIsNone(manifest["char_budget"]["min_chars"])
            self.assertEqual(manifest["char_budget"]["max_chars"], 18000)
            self.assertIn("本批 3 段", card)

    def test_track_alias_variants(self):
        for brief, expect in (
            ("| 生成模型轨 | **Wan3.0** | 用户指定 |", "wan30"),
            ("| 生成轨 | Seedance 2.5 |", "seedance25"),
            ("| 生成轨 | MiniMax H3 |", "h3"),
            ("| 生成模型 | Wan3.0（`--model wan30` 轨；不与 Seedance 2.5 轨混用） |", "wan30"),
        ):
            with tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d), BRIEF.replace("| 生成轨 | wan30 |", brief))
                card = handoff.build_card(work, "4", "E01-SH01")
                self.assertIn(f"【唯一生成轨】{expect}", card)

    def test_missing_track_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF.replace("| 生成轨 | wan30 |\n", ""))
            with self.assertRaises(ValueError):
                handoff.build_card(work, "4", "E01-SH01")

    def test_duplicate_track_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF + "\n| 生成轨 | seedance25 |\n")
            with self.assertRaises(ValueError):
                handoff.build_card(work, "4", "E01-SH01")

    def test_invalid_track_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), BRIEF.replace("wan30", "seedance20"))
            with self.assertRaises(ValueError):
                handoff.build_card(work, "4", "E01-SH01")

    def test_missing_upstream_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "04-片段规划与逐镜表.md").unlink()
            with self.assertRaises(ValueError):
                handoff.build_card(work, "4", "E01-SH01")

    def test_stage4_segment_must_be_frozen(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            with self.assertRaises(ValueError):
                handoff.build_card(work, "4", "E01-SH09")
            # 冻结表内的片段正常通过
            card = handoff.build_card(work, "4", "E01-SH01~SH02")
            self.assertIn("E01-SH01", card)

    def test_stage3_card(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "02a-结构化拍摄剧本.json").write_text(
                json.dumps({"segments": [{"episode": 1}]}), encoding="utf-8")
            card = handoff.build_card(work, "3", "E01-SH01")
            self.assertIn("R27", card)
            self.assertIn("R36", card)
            self.assertIn("crosscheck_storyboard", card)
            self.assertNotIn("validate_compact_package.py", card)
            self.assertNotIn("<本批临时包>", card)

    def test_manifest_matches_card(self):
        """改造一：manifest 与派单卡同源；口径、哈希、批次 ID 必须对得上。"""
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            card = handoff.build_card(work, "4", "E01-SH01~SH02")
            manifest = handoff.build_manifest(work, "4", "E01-SH01~SH02", card)
            self.assertEqual(manifest["track"], "wan30")
            self.assertEqual(manifest["segments"], ["E01-SH01", "E01-SH02"])
            self.assertIsNone(manifest["char_budget"]["min_chars"])
            self.assertEqual(manifest["card_sha256"], handoff.wc.sha256_text(card))
            self.assertEqual(manifest["state"], "待写")
            upstream = {u["label"]: u for u in manifest["upstream"]}
            table = upstream["片段规划与逐镜表（冻结版）"]
            self.assertTrue(table["present"])
            self.assertEqual(len(table["sha256"]), 64)
            boundary = upstream["阶段1冻结片段边界与对白/动作容量"]
            self.assertTrue(boundary["present"])
            self.assertEqual(boundary["path"], "内部/04a-片段边界.json")
            card_id = re.search(r"批次 ID：([^；\n]+)", card).group(1)
            self.assertEqual(card_id, manifest["batch_id"])
            self.assertEqual(set(manifest["continuity_upstream"]), {"E01-SH01", "E01-SH02"})
            self.assertTrue(all(len(value) == 64 for value in manifest["continuity_upstream"].values()))

    def test_stage4_requires_continuity_facts(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "04c-衔接事实.json").unlink()
            for build in (lambda: handoff.build_card(work, "4", "E01-SH01"),
                          lambda: handoff.build_manifest(work, "4", "E01-SH01", "card")):
                with self.assertRaisesRegex(ValueError, "衔接事实"):
                    build()

    def test_manifest_requires_fact_for_each_assigned_segment(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            path = work / "内部" / "04c-衔接事实.json"
            facts = json.loads(path.read_text(encoding="utf-8"))
            facts["segments"] = facts["segments"][:1]
            path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "衔接事实缺本批片段"):
                handoff.build_manifest(work, "4", "E01-SH01~SH02", "card")

    def test_stage4_card_and_manifest_include_only_matching_space_contracts(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            space = work / "内部" / "04b-站位图"
            space.mkdir()
            base = space / "SCENE_LOC_01_客厅.json"
            base.write_text(json.dumps({"scene": "客厅"}), encoding="utf-8")
            first = space / "E01_SH01_S01.json"
            first.write_text(json.dumps({"base": "SCENE_LOC_01_客厅", "shot": "E01_SH01_S01"}), encoding="utf-8")
            # A neighboring segment is not part of this handoff and must stay out.
            unrelated = space / "E01_SH02_S01.json"
            unrelated.write_text(json.dumps({"base": "SCENE_LOC_01_客厅", "shot": "E01_SH02_S01"}), encoding="utf-8")

            card = handoff.build_card(work, "4", "E01-SH01")
            self.assertIn("SCENE_LOC_01_客厅.json", card)
            self.assertIn("E01_SH01_S01.json", card)
            self.assertNotIn("E01_SH02_S01.json", card)
            self.assertIn("不扫描04b全目录", card)
            self.assertIn("不输出数值坐标", card)

            manifest = handoff.build_manifest(work, "4", "E01-SH01", card)
            space_rows = [row for row in manifest["upstream"] if row["label"].startswith(("站位场景基底", "镜级站位增量"))]
            self.assertEqual([row["path"] for row in space_rows], [
                "内部/04b-站位图/SCENE_LOC_01_客厅.json",
                "内部/04b-站位图/E01_SH01_S01.json",
            ])

    def test_stage4_space_increment_missing_base_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            space = work / "内部" / "04b-站位图"
            space.mkdir()
            (space / "E01_SH01_S01.json").write_text(
                json.dumps({"base": "SCENE_LOC_01_MISSING", "shot": "E01_SH01_S01"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "场景基底不存在"):
                handoff.build_card(work, "4", "E01-SH01")

    def test_manifest_fails_closed_without_upstream(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "04-片段规划与逐镜表.md").unlink()
            with self.assertRaises(ValueError):
                handoff.build_manifest(work, "4", "E01-SH01", "")

    def test_same_range_has_distinct_stage_ids(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "02a-结构化拍摄剧本.json").write_text(
                json.dumps({"segments": [{"episode": 1}]}), encoding="utf-8")
            manifests = []
            for stage in ("3", "4"):
                card = handoff.build_card(work, stage, "E01-SH01")
                manifest = handoff.build_manifest(work, stage, "E01-SH01", card)
                self.assertEqual(re.search(r"批次 ID：([^；\n]+)", card).group(1), manifest["batch_id"])
                manifests.append(manifest)
            self.assertNotEqual(manifests[0]["batch_id"], manifests[1]["batch_id"])

    def test_card_required_read_paths_exist(self):
        for stage, brief in (("3", BRIEF), ("4", BRIEF), ("4", BRIEF_SEEDANCE), ("4", BRIEF_H3)):
            with self.subTest(stage=stage, brief=brief), tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d), brief)
                (work / "内部" / "02a-结构化拍摄剧本.json").write_text(
                    json.dumps({"segments": [{"episode": 1}]}), encoding="utf-8")
                card = handoff.build_card(work, stage, "E01-SH01")
                required = card.split("【必读（白名单）】", 1)[1].split("【上游输入】", 1)[0]
                paths = [line[2:].split("#", 1)[0] for line in required.splitlines() if line.startswith("- ")]
                self.assertTrue(paths)
                self.assertIn(str(ROOT / "references" / "content-expression.md"), paths)
                self.assertIn("R38", card)
                for path in paths:
                    self.assertTrue(Path(path).is_file(), path)

    def test_stage4_requires_fight_route_even_without_fight(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "04b-打斗路由判定表.md").unlink()
            for build in (lambda: handoff.build_card(work, "4", "E01-SH01"),
                          lambda: handoff.build_manifest(work, "4", "E01-SH01", "")):
                with self.assertRaisesRegex(ValueError, "打斗路由"):
                    build()

    def test_review_conclusion_after_evidence_subheading_is_valid(self):
        text = """# 剧情独立评审
评审人：独立评稿员
未关闭阻断/重要缺陷：0
## 事件/分集
### 证据
事件因果链已逐项复核。
结论：通过
## 逐集剧本
### 证据
逐场目标与冲突已复核。
结论：通过
## 片段规划
### 证据
片段边界与估时已复核。
结论：通过
"""
        labels = ("事件/分集", "逐集剧本", "片段规划")
        self.assertEqual(handoff._review_sections_pass(text, labels), [])
        missing_first = text.replace("结论：通过", "结论：待整改", 1)
        errors = handoff._review_sections_pass(missing_first, labels)
        self.assertTrue(any("事件/分集" in error for error in errors), errors)
        self.assertEqual(len(errors), 1, errors)

    def test_manifest_records_policy_snapshot(self):
        """改造六：快照必须带版本号与 policy 哈希，台账才能发现规范漂移。"""
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            manifest = handoff.build_manifest(work, "4", "E01-SH01", "card")
            snap = manifest["policy"]
            self.assertIsInstance(snap["policy_version"], int)
            self.assertEqual(len(snap["policy_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
