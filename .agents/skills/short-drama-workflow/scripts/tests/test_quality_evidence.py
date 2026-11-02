#!/usr/bin/env python3
"""证据门行为回归：覆盖真实范围、修改失效、伪引文、缺评审和阶段路由。"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quality_evidence as quality
import validate_stage_artifacts as gates
import workflow_common as wc
import build_handoff as handoff


def fixture(root: Path) -> Path:
    internal = root / "内部"
    internal.mkdir(parents=True)
    (internal / "00-项目输入单.md").write_text("| 生成轨 | wan30 |\n项目设定是写实剧情。")
    (internal / "03-资产与空间设计.md").write_text("当代泰国背景，自然光与灰褐色；两人在前向座椅上坐稳。")
    (internal / "03a-固定资产图片提示词.md").write_text(
        "### 角色 CHAR_01｜娜琳\n#### 图片提示词\n```text\n米白上衣，红绳在左腕。\n```\n"
        "### 场景 LOC_01｜车内\n#### 图片提示词\n```text\n前后座朝车头，前排椅背在后排前方。\n```\n")
    (internal / "04-片段规划与逐镜表.md").write_text(
        "## E01/SH01｜车内（30秒）\n场景：LOC_01｜角色：CHAR_01\n"
        "| 镜 | 时间 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 内容要点 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| S01 | 0-30 | 中景 | 35mm | 侧45度平视 | 跟移 | 浅 | 娜琳坐在后排。 |\n")
    (internal / "04c-衔接事实.json").write_text('{"schema":"continuity-facts/2"}')
    package = root / "精简制作包.md"
    package.write_text(
        "# 精简制作包\n## 固定资产\n## 剧集 E01｜车内\n"
        "### 小说原文\n```text\n娜琳坐在后排。\n```\n"
        "### 片段 SH01｜30秒｜车内\n角色：CHAR_01\n场景：LOC_01\n"
        "#### 视频提示词\n```text\n娜琳坐在后排，朝向车头。\n```\n")
    return root


def simulated_review(root: Path, stage: str) -> tuple[Path, dict]:
    """仅供临时测试项目的模拟评审，禁止调用于用户作品。"""
    data = quality.initialize(root, stage)
    data["authors"] = ["test-author"]
    data["reviewer"] = {"id": "test-reviewer", "independent": True}
    for row in data["items"]:
        for item in row["checks"].values():
            item.update(status="pass", finding="测试用判断：对照后排座椅和朝向核对该条，不代表真实独立评审。",
                        evidence=[{"file": "内部/03-资产与空间设计.md", "quote": "两人在前向座椅上坐稳"}])
    path = root / "内部" / quality.FILES[stage]
    path.write_text(json.dumps(data, ensure_ascii=False))
    return path, data


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = fixture(Path(self.tmp.name))

    def test_missing_record_fails(self):
        self.assertIn("缺逐项语义", "".join(quality.check(self.root, "2")))

    def test_init_does_not_sign_pass(self):
        data = quality.initialize(self.root, "2")
        self.assertEqual({r["id"] for r in data["items"]}, {"CHAR_01", "LOC_01"})
        self.assertTrue(all(c["status"] == "pending" for r in data["items"] for c in r["checks"].values()))
        p = self.root / "内部" / quality.FILES["2"]
        p.write_text(json.dumps(data))
        self.assertTrue(quality.check(self.root, "2"))

    def test_complete_text_review_allows_pending_images(self):
        for stage in ("2", "3", "4"):
            simulated_review(self.root, stage)
            self.assertEqual(quality.check(self.root, stage), [], stage)

    def test_shot_and_segment_scope_derived_from_outputs(self):
        self.assertEqual(set(quality.initialize(self.root, "3")["items"][0]["checks"]), set(quality.CHECKS["3"]))
        self.assertEqual(quality.initialize(self.root, "3")["items"][0]["id"], "E01-SH01-S01")
        self.assertEqual(quality.initialize(self.root, "4")["items"][0]["id"], "E01-SH01")

    def test_coverage_hole_and_duplicate_fail(self):
        path, doc = simulated_review(self.root, "2")
        doc["items"].append(doc["items"][0])
        doc["items"] = [r for r in doc["items"] if r["id"] != "LOC_01"]
        path.write_text(json.dumps(doc))
        errors = "".join(quality.check(self.root, "2"))
        self.assertIn("验收项重复", errors)
        self.assertIn("范围不完整", errors)

    def test_asset_change_invalidates_review(self):
        simulated_review(self.root, "2")
        with (self.root / "内部/03a-固定资产图片提示词.md").open("a") as f:
            f.write("新增装饰")
        self.assertIn("版本过期", "".join(quality.check(self.root, "2")))

    def test_new_item_cannot_hide_under_old_coverage(self):
        simulated_review(self.root, "2")
        with (self.root / "内部/03a-固定资产图片提示词.md").open("a") as f:
            f.write("\n### 道具 PROP_01｜手机\n#### 图片提示词\n```text\n黑色手机\n```\n")
        self.assertIn("PROP_01", "".join(quality.check(self.root, "2")))

    def test_same_author_and_reviewer_fails(self):
        path, doc = simulated_review(self.root, "2")
        doc["reviewer"]["id"] = doc["authors"][0]
        path.write_text(json.dumps(doc))
        self.assertIn("不同执行者", "".join(quality.check(self.root, "2")))

    def test_fake_quote_and_open_defect_fail(self):
        path, doc = simulated_review(self.root, "2")
        doc["items"][0]["checks"]["style"]["evidence"][0]["quote"] = "原文中没有这一句"
        doc["defects"] = [{"status": "open", "resolution": ""}]
        path.write_text(json.dumps(doc))
        errors = "".join(quality.check(self.root, "2"))
        self.assertIn("证据引文不存在", errors)
        self.assertIn("未关闭", errors)

    def test_not_applicable_requires_reason_and_evidence(self):
        path, doc = simulated_review(self.root, "2")
        doc["items"][0]["checks"]["style"] = {"status": "not_applicable", "finding": "", "evidence": []}
        path.write_text(json.dumps(doc))
        errors = "".join(quality.check(self.root, "2"))
        self.assertIn("不适用项也须说明原因", errors)
        self.assertIn("缺指向", errors)

    def test_missing_upstream_and_empty_scope_do_not_pass(self):
        (self.root / "内部/03a-固定资产图片提示词.md").write_text("# 没有资产")
        with self.assertRaisesRegex(ValueError, "空清单"):
            quality.initialize(self.root, "2")

    def test_one_segment_without_shots_cannot_hide_in_other_segments(self):
        board = self.root / "内部/04-片段规划与逐镜表.md"
        board.write_text(board.read_text() + "\n## E01/SH02｜未补分镜\n只有剧情摘要。\n")
        with self.assertRaisesRegex(ValueError, "E01-SH02 缺实际逐镜表"):
            quality.initialize(self.root, "3")

    def test_duplicate_prompt_not_silently_reviewed(self):
        p = self.root / "精简制作包.md"
        p.write_text(p.read_text() + "\n#### 视频提示词\n```text\n另一个提示词\n```\n")
        with self.assertRaisesRegex(ValueError, "重复"):
            quality.initialize(self.root, "4")

    def test_review_and_asset_changes_invalidate_gate_receipt_inputs(self):
        simulated_review(self.root, "2")
        before = wc.stage_gate_inputs(self.root, "2")
        path = self.root / "内部" / quality.FILES["2"]
        path.write_text(path.read_text() + "\n ")
        self.assertNotEqual(before, wc.stage_gate_inputs(self.root, "2"))
        assets = self.root / "内部/03a-固定资产图片提示词.md"
        assets.write_text(assets.read_text() + "\n")
        self.assertIn("内部/03a-固定资产图片提示词.md", wc.stage_gate_inputs(self.root, "2"))

    def test_checked_images_require_actual_hashed_files(self):
        path, doc = simulated_review(self.root, "2")
        doc["image_review"] = "checked"
        path.write_text(json.dumps(doc))
        self.assertIn("未锁定任何实际图片", "".join(quality.check(self.root, "2")))

    def test_malformed_status_returns_errors(self):
        path, doc = simulated_review(self.root, "2")
        doc["image_review"] = []
        doc["items"][0]["checks"]["style"]["status"] = []
        path.write_text(json.dumps(doc))
        self.assertTrue(quality.check(self.root, "2"))

    def test_padded_author_name_cannot_self_sign(self):
        path, doc = simulated_review(self.root, "2")
        doc["reviewer"]["id"] = " test-author "
        path.write_text(json.dumps(doc))
        self.assertIn("不同执行者", "".join(quality.check(self.root, "2")))

    def test_stage_cli_requires_evidence_even_if_old_checks_pass(self):
        with patch.object(gates, "stage2", side_effect=lambda *_: ([], [])), \
             patch.object(gates.workflow_manifest, "check_review_stage1"), \
             patch.object(sys, "argv", ["gate", str(self.root), "--stage", "2"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gates.main(), 1)
            simulated_review(self.root, "2")
            self.assertEqual(gates.main(), 0)

    def test_handoff_does_not_accept_old_zero_error_receipt_alone(self):
        (self.root / "内部/01c-剧情评审.md").write_text(
            "评审人：test-reviewer\n未关闭阻断/重要缺陷：0\n"
            "## 事件/分集\n结论：通过\n## 逐集剧本\n结论：通过\n## 片段规划\n结论：通过\n")
        (self.root / "内部/03b-资产评审.md").write_text("评审人：test-reviewer\n结论：通过\n未关闭阻断/重要缺陷：0\n")
        with patch.object(handoff, "_gate_receipt_errors", return_value=[]):
            self.assertTrue(any("逐项语义" in x for x in handoff.check_stage_unlock(self.root, "3")))
            simulated_review(self.root, "2")
            self.assertEqual(handoff.check_stage_unlock(self.root, "3"), [])

    def test_stage3_runs_geometry_in_addition_to_review(self):
        space = self.root / "内部/04b-站位图"
        space.mkdir()
        # 临时空壳基底必须被几何门拦住，不能凭文字评审记录通过。
        (space / "SCENE_LOC_01.json").write_text('{"characters":[],"camera":{}}')
        simulated_review(self.root, "3")
        output = io.StringIO()
        with patch.object(gates, "stage3", side_effect=lambda *_: ([], [])), \
             patch.object(sys, "argv", ["gate", str(self.root), "--stage", "3"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(gates.main(), 1)
        self.assertIn("站位几何", output.getvalue())


if __name__ == "__main__":
    unittest.main()
