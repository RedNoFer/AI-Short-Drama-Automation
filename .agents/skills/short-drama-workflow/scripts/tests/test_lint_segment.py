#!/usr/bin/env python3
"""lint_segment.py（单段即写即检）的回归自测。

运行：python3 scripts/tests/test_lint_segment.py

覆盖：
  · 好片段 → 校验器与（wan30）反例审计都通过；
  · 硬错误（三人「并肩」）→ wan30 lint 拦下；语义风险显示待评，不擅自改写；
  · 时间轴断档的片段 → 拦下；
  · 显式 --model 与输入单登记轨不一致 → 失败关闭（R37）；
  · 源文件缺资产区 → 明确报错而不是让绑定校验失真。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lint_segment", ROOT / "scripts" / "lint_segment.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

fixture_spec = importlib.util.spec_from_file_location(
    "compact_validator_test_fixtures", ROOT / "scripts" / "tests" / "test_compact_validator.py")
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)

POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))

WAN_LINT_ROWS = "\n".join([
    "0-5秒，镜头：中景，侧前方平视，沿道路短跟。阿泽迈步走近后停下，低头看向脚边。",
    "5-10秒，硬切，镜头：近景，左侧平视，短推。阿泽抬手扶住衣襟，侧身避开迎面风。",
    "10-15秒，硬切，镜头：中景，右侧微俯，向右短移。阿泽蹲下，伸手按住地面后站起。",
    "15-20秒，硬切，镜头：近景，左后方平视，轻移焦。阿泽回头望向来路，随后转身向前。",
    "20-25秒，硬切，镜头：中景，右前方平视，短跟。阿泽迈步跨过地面裂缝，抬手指向前方。",
    "25-30秒，硬切，镜头：远景，侧后方平视，短拉开。阿泽收回手臂，继续迈步走远。",
])


def write_project(tmp: Path, package_md: str, track: str = "wan30") -> Path:
    internal = tmp / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(
        f"# 项目输入单\n\n| 生成轨 | {track} |\n", encoding="utf-8")
    src = tmp / "精简制作包.md"
    src.write_text(package_md, encoding="utf-8")
    return src


def run_cli(src: Path, seg: str, *extra) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lint_segment.py"), str(src), "--segment", seg, *extra],
        capture_output=True, text=True)


class LintSegmentTests(unittest.TestCase):
    def test_good_segment_passes(self):
        # 各轨沿用各自角色卡版式；Wan短稿测试另外验证没有长度下限。
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), fixtures.make_package(), track="seedance25")
            proc = run_cli(src, "SH01")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("范围提醒", proc.stdout)

    def test_wan30_short_complete_segment_passes(self):
        """逐段lint同样取消长度下限，短而完整的合规样本应通过。"""
        with tempfile.TemporaryDirectory() as d:
            pkg = fixtures.make_package(ratio="9:16", rows=WAN_LINT_ROWS, lock="")
            pkg = pkg.replace("【公共总规范】", "【公共总规范】全员不看镜头。", 1)
            src = write_project(Path(d), pkg, track="wan30")
            proc = run_cli(src, "SH01", "--model", "wan30")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_wan30_segment_over_hard_cap_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = fixtures.make_package(ratio="9:16", rows=WAN_LINT_ROWS,
                                        pad="甲" * 18001, lock="")
            pkg = pkg.replace("【公共总规范】", "【公共总规范】全员不看镜头。", 1)
            src = write_project(Path(d), pkg, track="wan30")
            proc = run_cli(src, "SH01", "--model", "wan30")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("18000", proc.stdout + proc.stderr)

    def test_valid_warm_source_is_pending_review_not_local_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = fixtures.make_package(ratio='9:16', rows=WAN_LINT_ROWS, lock='')
            pkg = pkg.replace('【公共总规范】',
                              '【公共总规范】全员不看镜头。既有舞台暖金灯光照亮人物。', 1)
            src = write_project(Path(d), pkg, track='wan30')
            proc = run_cli(src, 'SH01', '--model', 'wan30')
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('warm_light', proc.stdout)
            self.assertIn('未获阶段4验收', proc.stdout)
            self.assertIn('pending', proc.stdout)

    def test_blocking_vocabulary_caught(self):
        bad_rows = fixtures.GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "20-25秒，硬切，身后车灯扫过",
            "20-25秒，硬切，三人并肩站在车灯下，身后光线缓慢变化", 1)
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), fixtures.make_package(rows=bad_rows))
            proc = run_cli(src, "SH01")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("并肩", proc.stdout + proc.stderr)

    def test_timeline_gap_caught(self):
        broken = fixtures.GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "10-15秒，硬切，", "16-20秒，硬切，", 1)
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), fixtures.make_package(rows=broken))
            proc = run_cli(src, "SH01")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("时间", proc.stdout + proc.stderr)

    def test_model_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), fixtures.make_package(), track="wan30")
            proc = run_cli(src, "SH01", "--model", "seedance25")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("不一致", proc.stderr)

    def test_missing_assets_fails_cleanly(self):
        package = fixtures.make_package().split("## 固定资产", 1)[1]
        package = "# 精简制作包\n\n" + package
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), package)
            proc = run_cli(src, "SH01")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("固定资产", proc.stderr)

    def test_missing_segment_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            src = write_project(Path(d), fixtures.make_package())
            proc = run_cli(src, "SH99")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("找不到片段", proc.stderr)

    def test_segment_block_not_truncated(self):
        """切块终点用下一个片段头的绝对位置：块必须完整含结尾围栏，且不含下一段。"""
        doc = (
            "# 精简制作包\n\n## 固定资产\n\n"
            "### 角色 CHAR_01｜阿泽\n\n#### 图片提示词\n\n```text\n生成16:9横版白底角色四视图设定图。\n```\n\n"
            "## 剧集 E01｜测试\n\n### 小说原文\n\n```text\n原文\n```\n\n"
            "### 片段 E01-SH01｜30秒｜第一段\n\n角色：CHAR_01\n\n#### 视频提示词\n\n"
            "```text\n【参考】CHAR_01＝阿泽\n【时间轴】\n0-30秒，他站着\n```\n\n"
            "### 片段 E01-SH02｜30秒｜第二段\n\n角色：CHAR_01\n\n#### 视频提示词\n\n"
            "```text\n【参考】CHAR_01＝阿泽\n【时间轴】\n0-30秒，他走开\n```\n"
        )
        block = lint.find_segment(doc, "E01-SH01")
        self.assertTrue(block.rstrip().endswith("```"), block[-40:])
        self.assertNotIn("E01-SH02", block)
        mini = lint.build_mini_package(doc, "E01-SH01")
        self.assertIn("他站着", mini)
        self.assertNotIn("他走开", mini)

    def test_mini_package_keeps_real_episode_and_fragment_for_space_join(self):
        doc = (
            "# 阶段 4 片段骨架\n\n## 剧集 E03\n\n"
            "### 片段 E03-SH01｜30秒｜盐田签约\n\n角色：CHAR_01\n场景：LOC_05\n\n"
            "#### 视频提示词\n\n```text\n【参考】CHAR_01＝娜琳\n【时间轴】\n"
            "0-30秒，镜头：人物在车边\n```\n"
        )
        assets = (
            "# 精简制作包\n\n## 固定资产\n\n### 角色 CHAR_01｜娜琳\n\n"
            "#### 图片提示词\n\n```text\n娜琳人物资产。\n```\n\n"
            "### 场景 LOC_05｜盐田土路停车处\n\n#### 图片提示词\n\n```text\n场景资产。\n```\n"
        )
        mini = lint.build_mini_package(doc, "E03-SH01", assets)
        self.assertIn("## 剧集 E03｜lint-segment", mini)
        self.assertIn("### 片段 SH01｜30秒", mini)
        self.assertNotIn("E99", mini)

    def test_assets_from_other_package(self):
        """骨架草稿没有资产区时，--assets 指向制作包即可补资产。"""
        skeleton = (
            "# 阶段 4 片段骨架\n\n## 剧集 E01\n\n"
            "### 片段 E01-SH01｜30秒｜第一段\n\n角色：CHAR_01\n\n#### 视频提示词\n\n"
            "```text\n【参考】CHAR_01＝阿泽\n【时间轴】\n0-30秒，他站着\n```\n"
        )
        package = (
            "# 精简制作包\n\n## 固定资产\n\n### 角色 CHAR_01｜阿泽\n\n#### 图片提示词\n\n"
            "```text\n生成16:9横版白底角色四视图设定图。\n```\n"
        )
        mini = lint.build_mini_package(skeleton, "E01-SH01", package)
        self.assertIn("## 固定资产", mini)
        self.assertIn("CHAR_01", mini)

    def test_stage2_asset_prompt_source_is_mapped_and_filtered(self):
        """阶段4骨架可直接用03a资产原文lint，且只带本段实际绑定资产。"""
        skeleton = (
            "# 阶段 4 片段骨架\n\n## 剧集 E01\n\n"
            "### 片段 E01-SH01｜30秒｜第一段\n\n角色：CHAR_01\n场景：LOC_01\n道具：PROP_01\n\n"
            "#### 视频提示词\n\n```text\n【参考】CHAR_01＝阿泽；LOC_01＝房间\n"
            "【时间轴】\n0-30秒，角色在房间里\n```\n"
        )
        source_assets = (
            "# 固定资产图片提示词\n\n"
            "### CHAR-01｜阿泽\n人物9:16正面全身塑像图，身穿灰衣。\n\n"
            "### 道具 PROP-01｜钥匙\n16:9单件产品图。\n\n"
            "### 道具 PROP-02｜未使用的水杯\n16:9单件产品图。\n\n"
            "### SCENE_LOC_01｜房间\n16:9空镜全景，只有房间空间。\n"
        )
        mini = lint.build_mini_package(skeleton, "E01-SH01", source_assets)
        self.assertIn("### 角色 CHAR_01｜阿泽", mini)
        self.assertIn("### 场景 LOC_01｜房间", mini)
        self.assertIn("### 道具 PROP_01｜钥匙", mini)
        self.assertNotIn("### 道具 PROP_02", mini)
        self.assertIn("人物9:16正面全身塑像图", mini)

    def test_non_image_scene_space_note_is_not_mapped_as_asset(self):
        source_assets = (
            "# 固定资产图片提示词\n\n### SCENE_LOC_06｜车内\n"
            "本场景不制作空镜图片；车厢结构仅由空间JSON描述。\n"
        )
        mapped = lint.source_asset_section(source_assets)
        self.assertNotIn("### 场景 LOC_06", mapped)

    def test_find_brief_skips_sibling_non_input_00_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = write_project(root, fixtures.make_package())
            nested = root / "内部" / "派单" / "提示词骨架"
            nested.mkdir(parents=True)
            (root / "内部" / "派单" / "00-规则冲突裁决.md").write_text(
                "| 生成轨 | 错误值 |\n", encoding="utf-8")
            draft = nested / "骨架.md"
            draft.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            brief = lint.find_brief(draft)
            self.assertIn("| 生成轨 | wan30 |", brief)
            self.assertNotIn("错误值", brief)

    def test_default_asset_source_uses_project_stage2_prompts(self):
        """项目内派单草稿缺资产区时，默认回读冻结的03a，无须手工传路径。"""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_project(root, "# 草稿\n")
            draft = root / "内部" / "派单" / "提示词骨架" / "段.md"
            draft.parent.mkdir(parents=True)
            draft.write_text("# 草稿\n", encoding="utf-8")
            asset_source = root / "内部" / "03a-固定资产图片提示词.md"
            asset_source.write_text("# 固定资产图片提示词\n", encoding="utf-8")
            self.assertEqual(lint.find_default_asset_source(draft), asset_source)

    def test_default_asset_source_missing_outside_project_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            draft = Path(d) / "standalone.md"
            draft.write_text("# 草稿\n", encoding="utf-8")
            self.assertIsNone(lint.find_default_asset_source(draft))


if __name__ == "__main__":
    unittest.main()
