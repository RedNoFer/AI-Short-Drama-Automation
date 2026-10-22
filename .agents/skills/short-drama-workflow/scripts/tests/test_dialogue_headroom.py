#!/usr/bin/env python3
"""台词动作余量（dialogue share）的回归自测。

运行：python3 scripts/tests/test_dialogue_headroom.py

背景：S02 第88行原文是「按念白托底（中文约每秒5字），再往上留2-3秒给动作和呼吸」。
「+2–3 秒」在 30 秒片段×6–11 镜的结构里不可执行，本流水线改用占比口径：
台词占镜内时长超过 dialogue_share_warn（默认 75%）即提示镜内没有动作余量。

覆盖：短台词长镜不提醒；长台词短镜提醒；画外旁白等豁免；同片段多镜聚合成一条；
超 5.0 字/秒仍判错；policy 保留出处注记。
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))

LOCK = "声线锁定：CHAR_01 阿泽＝26岁男声，中低音清冷略沙。"

PACKAGE = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
生成16:9横版单张全景基准图。
```

## 剧集 E01｜测试集

### 小说原文

```text
第一集的小说原文。
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
【收尾】他走远。
```
"""

ROWS_CLEAN = [
    '0-4秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："走吧。"',
    '4-9秒，硬切，风吹过路面，他侧头听声。',
    '9-14秒，硬切，远处雾里有光，他向前一步。',
    '14-19秒，硬切，他停住脚步，眉头收紧。',
    '19-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
]

# 18 汉字 / 4 秒 = 4.5 字/秒：未超 5.0（不判错），但占镜内时长 90%（超过 75%）
ROWS_THIN = [
    '0-4秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："一二三四五六七八九十一二三四五六七八。"',
    '4-9秒，硬切，风吹过路面，他侧头听声。',
    '9-14秒，硬切，远处雾里有光，他向前一步。',
    '14-19秒，硬切，他停住脚步，眉头收紧。',
    '19-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
]

# 画外旁白：画面可独立给动作，不按动作余量提醒
ROWS_NARRATION = [
    '0-4秒，他站在雨里，镜头平视不动，画外旁白说："一二三四五六七八九十一二三四五六七八。"',
    '4-9秒，硬切，风吹过路面，他侧头听声。',
    '9-14秒，硬切，远处雾里有光，他向前一步。',
    '14-19秒，硬切，他停住脚步，眉头收紧。',
    '19-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
]

# 两镜都过紧，应聚合成一条提醒
ROWS_TWO_THIN = [
    '0-4秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："一二三四五六七八九十一二三四五六七八。"',
    '4-8秒，硬切，他抬头，他作口型对白、口型同步，说："一二三四五六七八九十一二三四五六七。"',
    '8-14秒，硬切，远处雾里有光，他向前一步。',
    '14-19秒，硬切，他停住脚步，眉头收紧。',
    '19-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
]

# 30 汉字 / 4 秒 = 7.5 字/秒：超上限，同时占满镜内时长
ROWS_OVER = [
    '0-4秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十。"',
    '4-9秒，硬切，风吹过路面，他侧头听声。',
    '9-14秒，硬切，远处雾里有光，他向前一步。',
    '14-19秒，硬切，他停住脚步，眉头收紧。',
    '19-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
]


def run(rows: list[str]) -> tuple[list, list]:
    source = PACKAGE.format(lock=LOCK, rows="\n".join(rows))
    result = validator.validate(source, POLICY, model="seedance25")
    return result["errors"], result["warnings"]


def headroom(warnings: list) -> list:
    return [w for w in warnings if "动作余量" in w]


class DialogueHeadroomTest(unittest.TestCase):
    def test_short_line_has_no_headroom_warning(self):
        errors, warnings = run(ROWS_CLEAN)
        self.assertEqual([e for e in errors if "语速" in e], [])
        self.assertEqual(headroom(warnings), [])

    def test_long_line_in_short_shot_warns(self):
        errors, warnings = run(ROWS_THIN)
        self.assertEqual([e for e in errors if "语速" in e], [], "4.5 字/秒不应判错")
        self.assertEqual(len(headroom(warnings)), 1, warnings)
        self.assertIn("75%", headroom(warnings)[0])

    def test_narration_is_exempt(self):
        _, warnings = run(ROWS_NARRATION)
        self.assertEqual(headroom(warnings), [])

    def test_multiple_thin_shots_aggregate_into_one_warning(self):
        _, warnings = run(ROWS_TWO_THIN)
        lines = headroom(warnings)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("2 镜", lines[0])

    def test_over_rate_still_errors(self):
        errors, warnings = run(ROWS_OVER)
        self.assertTrue(any("语速" in e and "超 5.0" in e for e in errors), errors)
        self.assertEqual(len(headroom(warnings)), 1)

    def test_policy_keeps_provenance(self):
        voice = POLICY["voice"]
        self.assertEqual(voice["max_hanzi_per_sec"], 5.0)
        self.assertIn("S02", voice["max_hanzi_per_sec_source"])
        self.assertIn("念白托底", voice["max_hanzi_per_sec_source"])
        self.assertIn("改造", voice["max_hanzi_per_sec_note"])
        self.assertEqual(voice["dialogue_share_warn"], 0.75)

    def test_share_threshold_is_configurable(self):
        relaxed = json.loads(json.dumps(POLICY))
        relaxed["voice"]["dialogue_share_warn"] = 0.95
        source = PACKAGE.format(lock=LOCK, rows="\n".join(ROWS_THIN))
        result = validator.validate(source, relaxed, model="seedance25")
        self.assertEqual(headroom(result["warnings"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
