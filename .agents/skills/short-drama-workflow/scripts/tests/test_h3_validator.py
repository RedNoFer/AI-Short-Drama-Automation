#!/usr/bin/env python3
"""validate_compact_package.py 的 H3 轨回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_h3_validator.py
H3 轨（--model h3）改动规则后先跑本测试，再跑 test_compact_validator.py（Seedance/Wan 轨）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))

ASSETS = """## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
```
"""

BASE_BODY = """integrated_multimodal_description: [Shot 1] Live-action, a low medium shot frames the young man in the off-white shirt from <Subject 1> crouching beside the concrete marker in <Subject 2>, morning fog thinning over wet asphalt. The camera pushes in with small amplitude at slow speed as he presses a yellowed paper map flat on the car hood with both palms. The steady young man with a low, calm voice (S1) says: <d>[Chinese] 走完这一段，路就有了。</d> [Shot 2] At 00:06.500, the camera cuts to a close-up of his fingers sliding along the hand-drawn route line, the paper edge curling against the cold metal. [Shot 3] At 00:10.000, the shot cuts to the wide marker stone as he stands and looks down the empty road, fog pulling back toward the horizon.

overall_soundscape: Fog muffles distant traffic while paper creases against the metal hood. His shoes scrape gravel as he stands, and the low hum of a cooling engine fades under the wind.

non_diegetic_music: A single sustained cello note at a slow tempo with sparse muted piano taps, fading out before the last frame."""

REF_BODY = """subject_definitions:
<Subject 1> is the young man in <Picture 1>, with long dark hair and a blue cardigan.
<Subject 2> is the coastal road in <Picture 2>, with grey surf and pale morning light.

summary:
[reference generation] The target video shows <Subject 1> walking on the coast road.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the long dark hair and blue cardigan are retained.
<Subject 2> (appears in [Shot 1]): fully_preserved - the grey surf and pale morning light are retained.

detailed_description:
The target video is in a realistic live-action style.
[Shot 1] The shot begins from <Picture 1>, showing <Subject 1> walking along <Subject 2>. The camera tracks right with small amplitude at slow speed. <Subject 1> (S1) says softly, <d>[English] The wind keeps my pace.</d> Native speech estimate: 1.8s; pauses: 0.4s.

overall_soundscape: Steady surf and light wind continue beneath the whole clip.

non_diegetic_music: A restrained acoustic guitar pattern at a slow tempo with a low sustained pad underneath."""


def package(body: str, duration: int = 12, bindings: str = "角色：CHAR_01\n场景：LOC_01",
            extra: str = "") -> str:
    return f"""# 精简制作包

{ASSETS}
## 剧集 E01｜雾起

### 小说原文

```text
雾从路面漫上来。
```

### 片段 SH01｜{duration}秒｜零公里碑

{bindings}
{extra}
#### 视频提示词

```text
{body}
```
"""


class H3ValidatorTests(unittest.TestCase):
    def validate(self, source: str) -> dict:
        return validator.validate(source, POLICY, model="h3")

    def test_base_package_passes(self):
        result = self.validate(package(BASE_BODY))
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["mode"], "base")

    def test_ref2va_package_passes(self):
        result = self.validate(package(REF_BODY, duration=8))
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["mode"], "ref2va")

    def test_native_h3_missing_timing_rejected(self):
        body = REF_BODY.replace(" Native speech estimate: 1.8s; pauses: 0.4s.", "")
        result = self.validate(package(body, duration=8))
        self.assertTrue(any("非汉语实际台词" in e for e in result["errors"]), result)

    def test_native_h3_timing_must_be_outside_spoken_tag(self):
        body = REF_BODY.replace("</d> Native speech estimate: 1.8s; pauses: 0.4s.",
                                " Native speech estimate: 1.8s; pauses: 0.4s.</d>")
        result = self.validate(package(body, duration=8))
        self.assertTrue(any("非汉语实际台词" in e for e in result["errors"]), result)

    def test_native_h3_next_cut_defines_speech_window(self):
        body = BASE_BODY.replace("[Chinese] 走完这一段，路就有了。",
                                 "[Thai] แม่ฉันเหรอ?")
        body = body.replace("</d>", "</d> Native speech estimate: 6.2s; pauses: 0.4s.")
        result = self.validate(package(body))
        self.assertTrue(any("超过镜内6.5秒" in e for e in result["errors"]), result)

    def test_app_segment_duration_allowed_with_notice(self):
        """app 模式：片段时长沿用应用单位（30 秒），超官方单条上限只提醒。"""
        result = self.validate(package(BASE_BODY, duration=30))
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(any("单条输出上限" in w for w in result["warnings"]), result["warnings"])

    def test_official_segment_duration_enforced(self):
        """official 模式：强制 4–15 秒。"""
        result = validator.validate(package(BASE_BODY, duration=30), POLICY,
                                    model="h3", h3_segments="official")
        self.assertFalse(result["ok"])
        self.assertTrue(any("官方单条上限" in e for e in result["errors"]), result["errors"])

    def test_missing_field_rejected(self):
        body = BASE_BODY.replace("non_diegetic_music: A single sustained cello note at a slow tempo with sparse muted piano taps, fading out before the last frame.", "")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("non_diegetic_music" in e for e in result["errors"]), result["errors"])

    def test_four_section_markers_rejected(self):
        body = "【参考】\nCHAR_01=阿泽\n\n" + BASE_BODY
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("四段结构" in e for e in result["errors"]), result["errors"])

    def test_cut_not_increasing_rejected(self):
        body = BASE_BODY.replace("At 00:10.000", "At 00:05.000")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("严格递增" in e for e in result["errors"]), result["errors"])

    def test_cut_beyond_duration_rejected(self):
        body = BASE_BODY.replace("At 00:10.000", "At 00:14.000")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("超出片段时长" in e for e in result["errors"]), result["errors"])

    def test_dialogue_without_language_tag_rejected(self):
        body = BASE_BODY.replace("<d>[Chinese] 走完这一段，路就有了。</d>", "<d>走完这一段，路就有了。</d>")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("语言标签" in e for e in result["errors"]), result["errors"])

    def test_undefined_reference_label_rejected(self):
        body = REF_BODY.replace("The camera tracks right with small amplitude at slow speed.",
                                 "The camera tracks right with small amplitude at slow speed past <Subject 3>.")
        result = self.validate(package(body, duration=8))
        self.assertFalse(result["ok"])
        self.assertTrue(any("subject_definitions" in e for e in result["errors"]), result["errors"])

    def test_picture_label_without_alignment_line_rejected(self):
        body = BASE_BODY.replace("<Subject 2>", "<Picture 1>")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("对齐指令行" in e for e in result["errors"]), result["errors"])

    def test_over_char_limit_rejected(self):
        filler = " The camera holds on the empty road while the fog thins." * 150
        body = BASE_BODY.replace("The camera pushes in with small amplitude at slow speed",
                                 "The camera pushes in with small amplitude at slow speed" + filler)
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("超过本项目 H3 上限" in e for e in result["errors"]), result["errors"])

    def test_h3_prompt_between_seedance_default_and_h3_cap_passes(self):
        """H3's 6000-char cap must not inherit Seedance's 3000-char default."""
        filler = "The camera tracks across the wet road as the mist lifts from the tree line. " * 55
        body = BASE_BODY.replace("overall_soundscape:", filler + "\n\noverall_soundscape:")
        self.assertGreater(len(body), 3000)
        self.assertLess(len(body), 6000)
        result = self.validate(package(body))
        self.assertTrue(result["ok"], result["errors"])

    def test_first_frame_field_requires_picture_tag(self):
        extra = "\n#### 首帧提示词\n\n```text\n16:9 电影剧照：阿泽蹲在零公里碑旁。\n```\n"
        result = self.validate(package(BASE_BODY, extra=extra))
        self.assertFalse(result["ok"])
        self.assertTrue(any("首帧提示词" in e for e in result["errors"]), result["errors"])

    def test_picture_tag_without_first_frame_field_rejected(self):
        body = BASE_BODY.replace("[Shot 1] Live-action, a low medium shot",
                                 "[Shot 1] Live-action, starting from <Picture 1>, a low medium shot")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("首帧提示词" in e for e in result["errors"]), result["errors"])

    def test_first_frame_field_and_picture_tag_pass(self):
        extra = "\n#### 首帧提示词\n\n```text\n16:9 电影剧照：阿泽蹲在零公里碑旁。\n```\n"
        body = BASE_BODY.replace("[Shot 1] Live-action, a low medium shot",
                                 "[Shot 1] Live-action, starting from <Picture 1>, a low medium shot")
        aligned = ("For the target video, at 0.00 seconds into the target video, "
                   "<Picture 1> (from [Shot 1]) is fully referenced.\n\n" + body)
        result = self.validate(package(aligned, extra=extra))
        self.assertTrue(result["ok"], result["errors"])

    def test_subject_count_must_match_bindings(self):
        body = BASE_BODY.replace("crouching beside the concrete marker in <Subject 2>", "crouching beside the concrete marker")
        result = self.validate(package(body))
        self.assertFalse(result["ok"])
        self.assertTrue(any("一一对应" in e for e in result["errors"]), result["errors"])

    def test_other_tracks_unaffected(self):
        """H3 轨改动不得影响 Seedance/Wan 轨：同一份源用两轨解析仍按各自口径判定。"""
        seedance_source = package(BASE_BODY)
        result = validator.validate(seedance_source, POLICY, model="seedance25")
        self.assertFalse(result["ok"])  # H3 正文在 Seedance 轨缺四段结构，仍判不合格


if __name__ == "__main__":
    unittest.main(verbosity=2)
