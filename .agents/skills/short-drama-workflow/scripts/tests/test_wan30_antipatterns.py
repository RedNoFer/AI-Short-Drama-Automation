#!/usr/bin/env python3
"""audit_wan30_antipatterns.py 的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_wan30_antipatterns.py
新增/修改 WAN30-01 反例规则时先跑本测试。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "wan30_audit", ROOT / "scripts" / "audit_wan30_antipatterns.py"
)
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)
POLICY = ROOT / "policy.json"


def make_pkg(rows: str, public: str = "统一冷灰光影，真人实拍电影质感。") -> str:
    return f"""# 精简制作包

## 剧集 E01｜测试

### 片段 SH01｜30秒｜测试

#### 视频提示词

```text
【参考】CHAR_01=阿泽外观锁定；LOC_01=起点路段。
【公共总规范】{public}
【时间轴】
{rows}
【收尾】阿泽走远，下一片段承接。
```
"""


CLEAN_ROWS = "\n".join(
    [
        "0-10秒，镜头：中景，侧45°机位，手持轻晃。画面：阿泽伸手抓起绳头，转身把绳头甩上肩；苏晚抬手按住被风吹起的纸角。全员不看镜头，视线落在远处路牌。",
        "10-20秒，硬切。镜头：近景，右后方45°。画面：老杨蹲下，把绳头一圈圈收进掌心；小林退开半步，抬手擦掉额头的汗。全员不看镜头。",
        "20-30秒，硬切。镜头：全景，侧45°。画面：三个人错位站在车头两侧，阿泽弯腰抹轮眉，苏晚翻笔记本，老杨收绳，另两人留在画外只给肩线。全员不看镜头。",
    ]
)


class Wan30AntiPatternTests(unittest.TestCase):
    def _audit(self, rows: str, public: str = "统一冷灰光影，真人实拍电影质感。") -> dict:
        pkg = make_pkg(rows, public)
        tmp = ROOT / "scripts" / "tests" / "_tmp_wan30_audit.md"
        tmp.write_text(pkg, encoding="utf-8")
        try:
            return audit_mod.audit(tmp, POLICY)
        finally:
            tmp.unlink(missing_ok=True)

    def test_clean_rows_pass(self):
        result = self._audit(CLEAN_ROWS)
        self.assertEqual(result["errors"], 0, result["issues"])
        self.assertEqual(result["warnings"], 0, result["issues"])
        self.assertEqual(result["camera_missing_prefix"], 0)
        self.assertEqual(result["no_gaze_segments"], 0)

    def test_blocking_term_is_error(self):
        result = self._audit(CLEAN_ROWS.replace("三个人错位站在车头两侧", "五人并肩站在车头前", 1))
        self.assertGreater(result["errors"], 0)
        self.assertTrue(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_two_person_side_by_side_not_blocking(self):
        result = self._audit(
            "0-10秒，镜头：中景。画面：阿泽与老杨并肩走在车前，两人抬手扶住车门。全员不看镜头。"
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_dialogue_metaphor_not_blocking(self):
        result = self._audit(
            '0-10秒，镜头：中景。画面：阿泽抬手按住车顶，说："我们五人同心并肩。"全员不看镜头。'
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_shadow_lineup_not_blocking(self):
        result = self._audit(
            "0-10秒，镜头：全景。画面：晨光把五个人的影子排成一排，阿泽抬手关上车门。全员不看镜头。"
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_camera_must_be_front(self):
        long_desc = "晨雾漫过路面，" * 20
        result = self._audit(
            "0-10秒，" + long_desc + "阿泽站着，镜头：中景，侧45°。画面：他抬手。\n"
            "10-30秒，硬切。镜头：全景。画面：他转身走。全员不看镜头。"
        )
        self.assertGreater(result["camera_missing_prefix"], 0)
        self.assertTrue(any(i["kind"] == "camera_late" for i in result["issues"]))

    def test_still_life_too_long(self):
        result = self._audit(
            "0-5秒，包裹静置引擎盖，纸角被风掀起又落下。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起包裹，转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "still_life_too_long" for i in result["issues"]))

    def test_empty_shot_too_long(self):
        result = self._audit(
            "0-5秒，晨雾漫过路面，远处路牌在雾里若隐若现。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "empty_shot_too_long" for i in result["issues"]))

    def test_dialogue_shot_too_long(self):
        result = self._audit(
            '0-8秒，镜头：中景。画面：阿泽抬头，说："你好。"\n'
            "8-30秒，硬切。镜头：全景。画面：他转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "dialogue_shot_too_long" for i in result["issues"]))

    def test_warm_light_word(self):
        result = self._audit(CLEAN_ROWS, public="清晨低角度金色逆光，真人实拍。")
        self.assertTrue(any(i["kind"] == "warm_light" for i in result["issues"]))

    def test_legible_text_closeup(self):
        result = self._audit(
            "0-5秒，镜头：大特写。画面：字条上的墨色起笔清晰可读。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起字条，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "legible_text_closeup_risk" for i in result["issues"])
        )

    def test_missing_no_lens_gaze(self):
        result = self._audit(
            "0-30秒，镜头：中景。画面：阿泽伸手抓起绳头，转身走。"
        )
        self.assertTrue(any(i["kind"] == "missing_no_lens_gaze" for i in result["issues"]))

    def test_duplicate_timestamp_in_body(self):
        result = self._audit(
            "0-10秒，5秒，阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "duplicate_timestamp_in_body" for i in result["issues"])
        )

    def test_identity_overload(self):
        result = self._audit(
            "0-10秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠错位站在车头两侧，各自抬手整理装备。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "identity_overload" for i in result["issues"]))

    def test_five_person_shot_too_long(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：五人全景，阿泽、苏晚、老杨、许棠、小林错位站在车头两侧。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "five_person_shot_too_long" for i in result["issues"])
        )

    def test_five_person_face_overload(self):
        result = self._audit(
            "0-5秒，镜头：近景。画面：五人全景，阿泽、苏晚、老杨、许棠、小林站在车头前。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "five_person_face_overload" for i in result["issues"])
        )

    def test_group_dialogue_overload(self):
        result = self._audit(
            '0-8秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠围在车头，阿泽说："走。"全员不看镜头。'
        )
        self.assertTrue(
            any(i["kind"] == "group_dialogue_overload" for i in result["issues"])
        )

    def test_reflection_ambiguity(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：湖面倒影里站着阿泽，他抬手。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "reflection_ambiguity" for i in result["issues"])
        )

    def test_reflection_with_fantasy_tag_allowed(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：水下复刻倒影，幻境层，阿泽抬手。全员不看镜头。"
        )
        self.assertFalse(
            any(i["kind"] == "reflection_ambiguity" for i in result["issues"])
        )

    def test_group_shot_budget(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠错位站在车头两侧。全员不看镜头。\n"
            "5-10秒，硬切。镜头：中景。画面：阿泽、苏晚、老杨、小林围在引擎盖旁。全员不看镜头。\n"
            "10-30秒，硬切。镜头：中景。画面：阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "group_shot_budget" for i in result["issues"])
        )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
