#!/usr/bin/env python3
"""字幕公共层、当前片段边界及重复字段的正反用例。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prompt_contracts as contracts
import validate_compact_package as compact


def prompt(public="", row='0-5秒，娜琳（口型对白、口型同步）"你好。"。', ending="娜琳手握手机。"):
    return f"【参考】角色身份。\n【公共总规范】自然光。\n{public}\n【时间轴】\n{row}\n【收尾】{ending}"


class ContractTests(unittest.TestCase):
    def test_canonical_public_sentence_passes(self):
        self.assertEqual(contracts.check(prompt(contracts.wan_text_rule()), "wan30", "SH01"), [])

    def test_missing_changed_repeated_or_misplaced_sentence_fails(self):
        rule = contracts.wan_text_rule()
        for content in (prompt(), prompt(rule.replace("无字幕", "不需要字幕")),
                        prompt(rule + "\n" + rule), prompt(ending=rule),
                        prompt(row='0-5秒，娜琳（口型对白）"你好"。' + rule)):
            with self.subTest(content=content):
                self.assertTrue(any("TEXT-03" in e for e in contracts.check(content, "wan30", "SH01")))

    def test_pure_action_does_not_require_speech_rule(self):
        self.assertEqual(contracts.check(prompt(row="0-5秒，娜琳坐稳，只有风声。"), "wan30", "SH01"), [])

    def test_voiceover_and_inner_voice_are_covered(self):
        for tag in ("画外旁白", "心理独白", "画外延续", "心声：", "对白："):
            self.assertTrue(contracts.check(prompt(row=f'0-5秒，{tag}"你好"。'), "wan30", "SH01"))

    def test_cross_clip_directives_anywhere_are_rejected(self):
        for directive in ("下一片段人物走入。", "承接上段场景。", "为下一章切到门厅。", "next clip starts outside."):
            for content in (prompt(public=directive), prompt(row="0-5秒，" + directive), prompt(ending=directive)):
                self.assertTrue(any("跨片段" in e for e in contracts.check(content, "seedance25", "SH01")))

    def test_quoting_production_direction_does_not_bypass(self):
        self.assertTrue(contracts.check(prompt(ending='“下一片段人物走入。”'), "seedance25", "SH01"))

    def test_actual_dialogue_can_mention_next_part(self):
        self.assertEqual(contracts.check(prompt(row='0-5秒，口型对白、口型同步，"下一段路我自己走。"。'), "seedance25", "SH01"), [])

    def test_h3_speech_and_current_clip_cut_are_allowed(self):
        self.assertEqual(contracts.check('<d>[Chinese]下一段路我自己走。</d> At 00:05.000 [Shot 2] 门口近景。', "h3", "SH01"), [])
        self.assertTrue(contracts.check('<d>[Chinese]你好。</d> Next clip: entrance.', "h3", "SH01"))

    def test_missing_authority_fails_closed(self):
        with patch.object(contracts, "wan_text_rule", side_effect=ValueError("权威句缺失")):
            self.assertTrue(contracts.check(prompt(), "wan30", "SH01"))

    def test_duplicate_video_field_keeps_first_and_reports_error(self):
        package = ("# 精简制作包\n## 剧集 E01｜一\n### 片段 SH01｜30秒｜一\n角色：CHAR_01\n"
                   "#### 视频提示词\n```text\n第一个\n```\n#### 视频提示词\n```text\n第二个\n```\n")
        parsed = compact.parse_structure(package)
        self.assertTrue(any("重复" in e for e in parsed["errors"]))
        self.assertEqual(parsed["episodes"][0]["shots"][0]["prompts"]["视频提示词"], "第一个")

    def test_duplicate_binding_keeps_first_and_reports_error(self):
        package = "# 精简制作包\n## 剧集 E01｜一\n### 片段 SH01｜30秒｜一\n角色：CHAR_01\n角色：CHAR_02\n"
        parsed = compact.parse_structure(package)
        self.assertTrue(any("重复" in e for e in parsed["errors"]))
        self.assertEqual(parsed["episodes"][0]["shots"][0]["bindings"]["角色"], ["CHAR_01"])


if __name__ == "__main__":
    unittest.main()
