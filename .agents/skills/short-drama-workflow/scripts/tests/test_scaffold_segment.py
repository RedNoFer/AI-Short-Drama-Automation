#!/usr/bin/env python3
"""scaffold_segment.py（阶段 4 骨架派生）的回归自测。

运行：python3 scripts/tests/test_scaffold_segment.py

覆盖：
  · wan30：时间轴按 0.5 秒粒度逐镜转录、首镜无「硬切，」、其后每镜带「硬切，」；
  · 参考行从逐镜表资产代码派生（CHAR/LOC/PROP），不预写 @Image 编号；
  · 时间轴断档/未从 0 开始 → 失败关闭（不产出可提交骨架）；
  · Seedance 轨出现小数秒 → 失败关闭；
  · H3 轨 → 官方三字段骨架，不套四段结构；
  · 片段不存在 / 输入单缺生成轨 → 失败关闭；
  · 骨架头部写规范快照与上游哈希（改造六）。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("scaffold_segment", ROOT / "scripts" / "scaffold_segment.py")
scaffold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scaffold)

BRIEF = "# 00 项目输入单\n\n| 项 | 值 |\n|---|---|\n| 生成轨 | wan30 |\n"


def shots(spans: list[tuple[str, str]], size: str = "中景") -> str:
    head = ("| 镜 | 时间 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 内容要点 | 表演 |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for i, (start, end) in enumerate(spans, 1):
        content = "他抬头看门口" if i == 1 else f"他往前走一步（第{i}镜）"
        act = "P083 抢先开口｜极性：压场｜线索：下颌前送" if i == 3 else "—"
        rows.append(f"| S{i:02d} | {start}-{end} | {size} | 50mm | 侧45度平视 | 每秒约3度横移 | 浅 | {content} | {act} |")
    return head + "\n".join(rows) + "\n"


def board(spans_a=None, spans_b=None) -> str:
    a = spans_a or [("0", "4"), ("4", "7.5"), ("7.5", "12"), ("12", "16"),
                    ("16", "20.5"), ("20.5", "24"), ("24", "27"), ("27", "30")]
    b = spans_b or [("0", "4"), ("4", "8"), ("8", "12"), ("12", "16.5"),
                    ("16.5", "21"), ("21", "25"), ("25", "27.5"), ("27.5", "30")]
    return (
        "# 04-片段规划与逐镜表\n\n"
        "## E01/SH01｜扩音器响在大厅（30 秒 / 8 镜）\n\n"
        "场景：LOC_01｜角色：CHAR_01、CHAR_02｜道具：PROP_02\n\n"
        + shots(a) +
        "\n## E01/SH02｜谈恋爱时一起吃的饭（30 秒 / 8 镜）\n\n"
        "场景：LOC_01｜角色：CHAR_01｜道具：PROP_02\n\n"
        + shots(b)
    )


def make_project(tmp: Path, storyboard: str | None = None, track: str = "wan30") -> Path:
    internal = tmp / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(
        BRIEF.replace("wan30", track), encoding="utf-8")
    (internal / "04-片段规划与逐镜表.md").write_text(
        storyboard if storyboard is not None else board(), encoding="utf-8")
    return tmp


class ScaffoldTests(unittest.TestCase):
    def test_wan30_skeleton_axis(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            text, meta = scaffold.build_skeleton(work, "E01-SH01~SH02", None)
            self.assertEqual(meta["segments"], ["E01-SH01", "E01-SH02"])
            self.assertIsNone(meta["char_budget"]["min_chars"])
            self.assertEqual(meta["char_budget"]["max_chars"], 18000)
            self.assertIn("0-4秒，TODO", text)
            self.assertIn("4-7.5秒，硬切，TODO", text)
            self.assertEqual(text.count("硬切，TODO"), 14)  # 2 片段 × (8-1)
            self.assertIn("CHAR_01＝TODO", text)
            self.assertIn("LOC_01＝TODO", text)
            self.assertIn("PROP_02＝TODO", text)
            # 导入端按「### 片段 ID｜N秒｜标题」建卡，缺时长段整块会被判无法识别
            self.assertIn("### 片段 E01-SH01｜30秒｜扩音器响在大厅", text)
            self.assertIn("角色：CHAR_01＝TODO", text)
            self.assertNotIn("#### 参考", text)
            self.assertNotIn("@Image", text)
            self.assertNotIn("@图片", text)

    def test_header_has_snapshot_and_upstream_hash(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            text, meta = scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("policy v", text)
            self.assertIn("SHA-256", text)
            self.assertEqual(len(meta["board_sha256"]), 64)
            self.assertIn("policy_sha256", meta["policy"])

    def test_gap_in_axis_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            broken = [("0", "4"), ("5", "8"), ("8", "12"), ("12", "16"),
                      ("16", "20.5"), ("20.5", "24"), ("24", "27"), ("27", "30")]
            work = make_project(Path(d), board(spans_a=broken))
            with self.assertRaises(ValueError) as ctx:
                scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("断档", str(ctx.exception))

    def test_axis_must_start_at_zero(self):
        with tempfile.TemporaryDirectory() as d:
            broken = [("1", "4"), ("4", "8"), ("8", "12"), ("12", "16"),
                      ("16", "20"), ("20", "24"), ("24", "27"), ("27", "30")]
            work = make_project(Path(d), board(spans_a=broken))
            with self.assertRaises(ValueError) as ctx:
                scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("未从 0 开始", str(ctx.exception))

    def test_seedance_rejects_fractional_seconds(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), track="seedance25")
            with self.assertRaises(ValueError) as ctx:
                scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("整数秒", str(ctx.exception))

    def test_h3_uses_official_fields(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), track="h3")
            text, _ = scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("integrated_multimodal_description", text)
            self.assertIn("overall_soundscape", text)
            self.assertIn("non_diegetic_music", text)
            self.assertNotIn("【时间轴】", text)

    def test_unknown_segment_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            with self.assertRaises(ValueError) as ctx:
                scaffold.build_skeleton(work, "E01-SH09", None)
            self.assertIn("找不到片段", str(ctx.exception))

    def test_missing_track_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "00-项目输入单.md").write_text("# 输入单\n\n无轨\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                scaffold.build_skeleton(work, "E01-SH01", None)

    def test_missing_storyboard_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            (work / "内部" / "04-片段规划与逐镜表.md").unlink()
            with self.assertRaises(ValueError) as ctx:
                scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertIn("04-片段规划与逐镜表", str(ctx.exception))

    def test_warns_when_shot_band_off(self):
        with tempfile.TemporaryDirectory() as d:
            short = [("0", "10"), ("10", "20"), ("20", "30")]
            work = make_project(Path(d), board(spans_a=short))
            _, meta = scaffold.build_skeleton(work, "E01-SH01", None)
            self.assertTrue(any("镜数 3" in w for w in meta["warnings"]))


if __name__ == "__main__":
    unittest.main()
