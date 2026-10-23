#!/usr/bin/env python3
"""角色图片提示词美工字段的回归自测。

运行：python3 scripts/tests/test_character_prompt_fields.py

检查口径：九块字段（媒介画风／体态／骨相／眉眼鼻唇／妆面与皮肤／发型与发饰／
饰件／服装三层／版式）中任何一块缺席都报提醒；眉眼鼻唇按单项计，要求四者中
至少三项写出相对关系；「素颜」「无饰品」属显式决断，计入已写。
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

# 九块齐全的角色提示词
FULL_CHAR = (
    "生成16:9横版白底角色四视图设定图：左侧四分之一为正面身份特写，右侧同尺度正面全身、"
    "自身左侧90度全身、背面全身，脚底齐平、头脚完整。"
    "写实电影摄影质感，真人头身比例，皮肤可见毛孔细纹。"
    "26岁男性，清瘦体型，176cm，肩线平直，站姿挺拔。"
    "窄长脸，颧部不宽、下颌转折清晰，下巴略钝；眉骨清晰压眼，直眉，眼距适中、眼尾平，"
    "鼻梁挺直、鼻尖小而鼻翼窄，唇形偏薄、唇峰明显、嘴角平直，正面与侧面为同一条连续轮廓。"
    "素颜，不施妆，肤色冷白，无磨皮。"
    "黑色碎短发，中分缝略偏左，发际线清晰，发束层次分明，额前碎发轻垂。"
    "左耳一枚极简银质耳钉，无其他饰品。"
    "深灰防水冲锋衣，立领、袖口抽绳收口、侧拉链口袋，哑光防风面料带织物纹理与缝线，"
    "黑色机能长裤，深色防滑登山靴，袖口有轻微磨损。"
    "四视图同脸同装同体型，表情一致不漂移。避免不同脸、视图比例不一、截断头脚、可读文字与水印。"
)

# 缺妆面、缺饰件、缺骨相
THIN_CHAR = (
    "生成16:9横版白底角色四视图设定图：左侧四分之一为正面身份特写，右侧为同尺度正面全身、"
    "自身左侧90度全身、背面全身，脚底齐平、头脚完整。"
    "写实电影摄影质感，真人头身比例。"
    "26岁男性，清瘦体型，站姿挺拔。"
    "眉骨清晰，直眉，眼距适中，鼻梁挺直，唇形偏薄。"
    "黑色碎短发，发束层次分明。"
    "深灰防水冲锋衣，立领、袖口抽绳收口，哑光防风面料带缝线，黑色机能长裤，深色防滑登山靴。"
    "四视图同脸同装同体型。避免不同脸、截断头脚、水印。"
)

# 只写了眉，眉眼鼻唇不足三项
FACE_THIN_CHAR = FULL_CHAR.replace(
    "眉骨清晰压眼，直眉，眼距适中、眼尾平，"
    "鼻梁挺直、鼻尖小而鼻翼窄，唇形偏薄、唇峰明显、嘴角平直，"
    "正面与侧面为同一条连续轮廓。",
    "眉骨清晰，浓眉。"
)

PACKAGE = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
{char}
```

### 角色 CHAR_02｜小林

#### 图片提示词

```text
{char2}
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图：清晨公路，右侧灰色方形路牌，左侧柏油路面伸入薄雾，材质为沥青颗粒与金属漆。无人无车。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
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
【公共总规范】统一写实电影摄影质感。{lock}
【时间轴】
0-4秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："走吧。"
4-9秒，硬切，风吹过路面，他侧头听声。
9-14秒，硬切，远处雾里有光，他向前一步。
14-19秒，硬切，他停住脚步，眉头收紧。
19-25秒，硬切，身后车灯扫过，雨幕发亮。
25-30秒，硬切，他呼出白气，画面定住。
【收尾】他走远。
```
"""


def run(char: str, char2: str | None = None) -> list:
    source = PACKAGE.format(char=char, char2=char2 or char, lock=LOCK)
    result = validator.validate(source, POLICY, model="seedance25")
    return result["warnings"]


def art_warnings(warnings: list, code: str = "CHAR_01") -> list:
    return [w for w in warnings if "美工字段" in w and w.startswith(code)]


class CharacterPromptFieldsTest(unittest.TestCase):
    def test_full_prompt_has_no_warning(self):
        self.assertEqual(art_warnings(run(FULL_CHAR)), [])

    def test_missing_makeup_warns(self):
        lines = art_warnings(run(THIN_CHAR))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("妆面与皮肤", lines[0])

    def test_missing_bone_structure_warns(self):
        lines = art_warnings(run(THIN_CHAR))
        self.assertIn("骨相与脸型", lines[0])

    def test_missing_ornament_warns(self):
        lines = art_warnings(run(THIN_CHAR))
        self.assertIn("饰件", lines[0])

    def test_bare_face_statement_counts_as_decision(self):
        # 「素颜」与「无饰品」都写进 THIN_CHAR 后，这两组不再报
        char = THIN_CHAR.replace("黑色碎短发", "素颜，不施妆；无饰品。黑色碎短发")
        lines = art_warnings(run(char))
        self.assertEqual(len(lines), 1, lines)
        self.assertNotIn("妆面与皮肤", lines[0])
        self.assertNotIn("饰件", lines[0])
        self.assertIn("骨相与脸型", lines[0])

    def test_face_parts_shortfall_is_named(self):
        lines = art_warnings(run(FACE_THIN_CHAR))
        self.assertTrue(any("眉眼鼻唇缺" in line for line in lines), lines)
        self.assertIn("眼", [line for line in lines if "眉眼鼻唇缺" in line][0])

    def test_scene_asset_is_not_checked(self):
        warnings = run(FULL_CHAR)
        self.assertEqual([w for w in warnings if w.startswith("LOC_01")], [])

    def test_check_is_configurable(self):
        relaxed = json.loads(json.dumps(POLICY))
        relaxed["assets"]["character_prompt_groups"] = {}
        source = PACKAGE.format(char=THIN_CHAR, char2=THIN_CHAR, lock=LOCK)
        result = validator.validate(source, relaxed, model="seedance25")
        self.assertEqual([w for w in result["warnings"] if "美工字段" in w], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
