#!/usr/bin/env python3
"""crosscheck_storyboard.py 的回归自测。

运行：python3 scripts/tests/test_crosscheck_storyboard.py

对应 2026-10-23 审计缺口「视感自查是自报，无交叉校验」：
把「声明值 vs 实算值」和「配额超限」两侧都钉住，既要有该拦的用例，
也要有不误拦的用例（例外固定、第一档不套配额）。
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "crosscheck", ROOT / "scripts" / "crosscheck_storyboard.py")
cross = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cross)

HEAD = "# 04 分镜\n\n{stat}\n\n## E01-SH01\n\n"
TABLE_HEAD = "| 镜 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 固定 |\n|---|---|---|---|---|---|---|\n"


def rows(items: list[tuple]) -> str:
    return "".join("| " + " | ".join(str(c) for c in item) + " |\n" for item in items)


GOOD_ROWS = [
    ("S01", "大远景", "24mm", "正面平视", "极缓慢横移", "深", "否"),
    ("S02", "全景", "35mm", "侧45平视", "极缓慢横移", "深", "否"),
    ("S03", "中景", "50mm", "侧45微俯", "手持微晃跟拍", "浅", "否"),
    ("S04", "中近景", "85mm", "侧面90平视", "极缓推镜", "浅", "否"),
    ("S05", "特写", "50mm", "侧背平视", "极缓推镜", "浅", "否"),
    ("S06", "全景", "35mm", "背面平视", "缓慢拉镜", "深", "否"),
]
GOOD_STAT = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；机位角度种数=6；侧45占比=33.3%"


def doc(stat: str = GOOD_STAT, items: list[tuple] | None = None) -> str:
    return HEAD.format(stat=stat) + TABLE_HEAD + rows(items or GOOD_ROWS)


def clip_doc(clip_id: str, stat: str = GOOD_STAT,
             items: list[tuple] | None = None) -> str:
    return (f"## {clip_id}\n\n{stat}\n\n" + TABLE_HEAD
            + rows(items or GOOD_ROWS))


class CrosscheckTests(unittest.TestCase):
    # ---------- 不该误拦 ----------
    def test_valid_storyboard_passes(self):
        errors, _ = cross.check_text(doc())
        self.assertEqual(errors, [], errors)

    def test_emit_matches_declared(self):
        line = cross.emit(doc(stat=""))
        self.assertEqual(line, GOOD_STAT.replace("；", "；"))

    def test_exempt_fixed_not_in_quota(self):
        """重锤凝固/留白长镜是 E24 允许的例外，不占 10% 配额。"""
        items = list(GOOD_ROWS)
        items[2] = ("S03", "中景", "50mm", "侧45微俯", "固定", "浅", "重锤凝固")
        stat = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；机位角度种数=6；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertEqual(errors, [], errors)

    def test_tier1_skips_quota(self):
        """第一档不套小墨配额，只校验声明一致性。"""
        items = [
            ("S01", "全景", "35mm", "正面平视", "固定", "深", "是"),
            ("S02", "全景", "35mm", "正面平视", "固定", "深", "是"),
            ("S03", "全景", "35mm", "正面平视", "固定", "深", "是"),
            ("S04", "全景", "35mm", "正面平视", "固定", "深", "是"),
        ]
        stat = "视感统计：镜数=4；固定=4；固定占比=100%；焦段种数=1；机位角度种数=1；侧45占比=0%"
        errors, warnings = cross.check_text(doc(stat, items), tier="tier1_standard")
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("第一档" in w for w in warnings), warnings)

    # ---------- 该拦 ----------
    def test_missing_stats_line_is_error(self):
        errors, _ = cross.check_text(doc(stat=""))
        self.assertTrue(any("视感统计" in e for e in errors), errors)

    def test_missing_key_is_error(self):
        stat = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat))
        self.assertTrue(any("机位角度种数" in e and "缺键" in e for e in errors), errors)

    def test_declared_count_mismatch_is_error(self):
        stat = GOOD_STAT.replace("镜数=6", "镜数=7")
        errors, _ = cross.check_text(doc(stat))
        self.assertTrue(any("镜数" in e and "实算 6" in e for e in errors), errors)

    def test_declared_ratio_mismatch_is_error(self):
        stat = GOOD_STAT.replace("侧45占比=33.3%", "侧45占比=50%")
        errors, _ = cross.check_text(doc(stat))
        self.assertTrue(any("侧45占比" in e for e in errors), errors)

    def test_fixed_quota_over_limit_is_error(self):
        items = list(GOOD_ROWS)
        items[1] = ("S02", "全景", "35mm", "侧45平视", "固定", "深", "是")
        stat = "视感统计：镜数=6；固定=1；固定占比=16.7%；焦段种数=4；机位角度种数=6；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertTrue(any("固定镜头占比" in e for e in errors), errors)

    def test_consecutive_fixed_is_error(self):
        items = list(GOOD_ROWS)
        items[1] = ("S02", "全景", "35mm", "侧45平视", "固定", "深", "是")
        items[2] = ("S03", "中景", "50mm", "侧45微俯", "固定", "浅", "是")
        stat = "视感统计：镜数=6；固定=2；固定占比=33.3%；焦段种数=4；机位角度种数=6；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertTrue(any("连续固定" in e for e in errors), errors)

    def test_three_close_shots_is_error(self):
        items = list(GOOD_ROWS)
        items[3] = ("S04", "近景", "85mm", "侧面90平视", "极缓推镜", "浅", "否")
        items[4] = ("S05", "特写", "50mm", "侧背平视", "极缓推镜", "浅", "否")
        items[5] = ("S06", "大特写", "50mm", "背面平视", "缓慢拉镜", "浅", "否")
        stat = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；机位角度种数=6；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertTrue(any("连三近景" in e for e in errors), errors)

    def test_focal_variety_too_low_is_error(self):
        items = [tuple(list(r[:2]) + ["50mm"] + list(r[3:])) for r in GOOD_ROWS]
        stat = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=1；机位角度种数=6；侧45占比=33.3%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertTrue(any("焦段只有" in e for e in errors), errors)

    def test_angle_variety_too_low_is_error(self):
        items = [tuple(list(r[:3]) + ["正面平视"] + list(r[4:])) for r in GOOD_ROWS]
        stat = "视感统计：镜数=6；固定=0；固定占比=0%；焦段种数=4；机位角度种数=1；侧45占比=0%"
        errors, _ = cross.check_text(doc(stat, items))
        self.assertTrue(any("机位角度只有" in e for e in errors), errors)

    def test_missing_column_is_error(self):
        text = HEAD.format(stat=GOOD_STAT) + "| 镜 | 景别 | 焦段 | 运镜 |\n|---|---|---|---|\n| S01 | 全景 | 35mm | 横移 |\n"
        errors, _ = cross.check_text(text)
        self.assertTrue(any("缺列" in e and "机位" in e for e in errors), errors)

    def test_unreadable_size_is_error(self):
        items = list(GOOD_ROWS)
        items[0] = ("S01", "大场面", "24mm", "正面平视", "极缓慢横移", "深", "否")
        errors, _ = cross.check_text(doc(GOOD_STAT, items))
        self.assertTrue(any("景别" in e and "不可识别" in e for e in errors), errors)

    def test_no_table_is_error(self):
        errors, _ = cross.check_text("# 04 分镜\n\n只有散文，没有表。\n")
        self.assertTrue(any("逐镜表" in e for e in errors), errors)

    def test_multi_clip_file_checks_each_clip_against_its_own_stats(self):
        # 机位角度种数允许 ±1 的格式容差，因此要差 2 才能验证分段隔离。
        wrong = GOOD_STAT.replace("机位角度种数=6", "机位角度种数=4")
        source = clip_doc("E01-SH01") + "\n\n" + clip_doc("E01-SH02", stat=wrong)
        errors, _ = cross.check_text(source)
        self.assertTrue(any("E01-SH02" in e and "机位角度种数" in e for e in errors), errors)
        self.assertFalse(any("E01-SH01" in e for e in errors), errors)

    def test_multi_clip_segment_missing_stats_is_error(self):
        source = clip_doc("E01-SH01") + "\n\n## E01-SH02\n\n" + TABLE_HEAD + rows(GOOD_ROWS)
        errors, _ = cross.check_text(source)
        self.assertTrue(any("E01-SH02" in e and "视感统计" in e for e in errors), errors)

    def test_emit_prints_one_stats_line_per_clip(self):
        source = clip_doc("E01-SH01") + "\n\n## E01-SH02\n\n" + TABLE_HEAD + rows(GOOD_ROWS)
        emitted = cross.emit(source)
        self.assertEqual(len([line for line in emitted.splitlines() if "视感统计：" in line]), 2)
        self.assertTrue(emitted.startswith("E01-SH01：视感统计："), emitted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
