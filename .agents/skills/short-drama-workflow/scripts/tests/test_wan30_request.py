#!/usr/bin/env python3
"""Wan3.0 独立请求规格检查；与制作包镜头策略隔离。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_wan30_request as validator


def request(media=None, **parameters):
    result = {"model": "wan3.0-video", "input": {"prompt": "将视频向后延长，继续前一段人物的动作。"},
              "parameters": parameters}
    if media is not None:
        result["input"]["media"] = media
    return result


def media(kind, count=1):
    return [{"type": kind, "url": f"https://example.com/{kind}/{i}"} for i in range(count)]


class WanRequestTests(unittest.TestCase):
    def assert_pass(self, req, info=None, **kwargs):
        result = validator.check_request(req, info, **kwargs)
        self.assertEqual(result["errors"], [], result)
        return result

    def assert_fail(self, req, message, info=None, **kwargs):
        result = validator.check_request(req, info, **kwargs)
        self.assertTrue(any(message in error for error in result["errors"]), result)
        return result

    def test_defaults_and_direct_prompt_are_independent_of_package(self):
        result = self.assert_pass(request())
        self.assertEqual(result["scope"]["duration_seconds"], 5)
        self.assertIn("生成效果", " ".join(result["scope"]["not_checked"]))
        req = request()
        req["model"] = "wan3.0-video-prime"
        self.assert_pass(req)

    def test_no_video_duration_bounds_and_smart(self):
        for value in (2, 30, -1):
            self.assert_pass(request(duration=value))
        for value in (0, 1, 31, -2, True, 2.0, 2.5, "5", None, float("nan"), float("inf")):
            self.assert_fail(request(duration=value), "duration")

    def test_video_duration_has_no_invented_two_second_minimum(self):
        req = request(media("reference_video"), duration=1)
        result = self.assert_pass(req, {"0": {"duration_seconds": 1}})
        self.assertTrue(result["scope"]["video_duration_budget_verified"])
        for value in (0, -2, False, 1.5):
            self.assert_fail(request(media("reference_video"), duration=value), "duration",
                             {"0": {"duration_seconds": 1}})

    def test_video_plus_output_budget_boundary(self):
        info = {"0": {"duration_seconds": 15}}
        self.assert_pass(request(media("reference_video"), duration=15), info)
        self.assert_fail(request(media("reference_video"), duration=16), "输入视频加输出时长", info)
        self.assert_fail(request(media("reference_video"), duration=10 ** 400), "输入视频加输出时长", info)

    def test_default_duration_is_included_in_budget(self):
        result = self.assert_pass(request(media("reference_video")), {"0": {"duration_seconds": 15}})
        self.assertEqual(result["scope"]["duration_seconds"], 5)
        self.assertTrue(result["scope"]["video_duration_budget_verified"])

    def test_smart_duration_does_not_claim_budget_verified(self):
        result = self.assert_pass(request(media("reference_video"), duration=-1),
                                  {"0": {"duration_seconds": 15}})
        self.assertFalse(result["scope"]["video_duration_budget_verified"])
        self.assertTrue(any("平台确认" in warning for warning in result["warnings"]))
        self.assert_fail(request(media("reference_video"), duration=-1), "未完成时长验证")

    def test_video_and_audio_counts_and_totals_are_separate(self):
        assets = media("reference_video", 5) + media("reference_audio", 5)
        info = {str(i): {"duration_seconds": 3} for i in range(10)}
        result = self.assert_pass(request(assets, duration=15), info)
        self.assertEqual(result["scope"]["declared_media_seconds"],
                         {"reference_video": 15.0, "reference_audio": 15.0})
        for kind in ("reference_video", "reference_audio"):
            with self.subTest(kind=kind):
                self.assert_fail(request(media(kind, 6)), "数量 6 超过 5",
                                 {str(i): {"duration_seconds": 1} for i in range(6)})
                self.assert_fail(request(media(kind, 2)), "总时长 16 秒超过 15",
                                 {"0": {"duration_seconds": 8}, "1": {"duration_seconds": 8}})

    def test_single_media_duration_bounds(self):
        for kind in ("reference_video", "reference_audio"):
            for value in (1, 15, 1.5):
                self.assert_pass(request(media(kind), duration=2), {"0": {"duration_seconds": value}})
            for value in (0.5, 15.1, 10 ** 400):
                self.assert_fail(request(media(kind)), "单个时长须在",
                                 {"0": {"duration_seconds": value}})

    def test_missing_and_invalid_media_duration_is_not_zero(self):
        for kind in ("reference_video", "reference_audio"):
            self.assert_fail(request(media(kind)), "未完成时长验证")
            for value in (None, True, False, -1, 0, "5", float("nan"), float("inf"), float("-inf")):
                result = self.assert_fail(request(media(kind)), "未完成时长验证",
                                          {"0": {"duration_seconds": value}})
                self.assertIsNone(result["scope"]["declared_media_seconds"][kind])
                self.assertFalse(result["scope"]["video_duration_budget_verified"])

    def test_metadata_uses_actual_zero_based_media_indices(self):
        assets = media("reference_image") + media("reference_video") + media("reference_audio")
        self.assert_pass(request(assets), {"1": {"duration_seconds": 3}, "2": {"duration_seconds": 4}})
        self.assert_fail(request(assets), "未完成时长验证", {"0": {"duration_seconds": 3}})

    def test_image_limit_and_url(self):
        self.assert_pass(request(media("reference_image", 10)))
        self.assert_fail(request(media("reference_image", 11)), "数量 11 超过 10")
        self.assert_fail(request([{"type": "reference_image", "url": " "}]), ".url")

    def test_frames_and_reference_types_are_mutually_exclusive(self):
        self.assert_pass(request(media("first_frame") + media("last_frame")))
        self.assert_fail(request(media("last_frame")), "需要 first_frame")
        self.assert_fail(request(media("first_frame", 2)), "数量 2 超过 1")
        for kind in ("reference_image", "reference_video", "reference_audio", "file", "link"):
            self.assert_fail(request(media("first_frame") + media(kind)), "互斥",
                             {"1": {"duration_seconds": 1}})

    def test_file_link_exclusion_and_prompt_extend_default(self):
        for kind in ("file", "link"):
            self.assert_pass(request(media(kind)))
            self.assert_fail(request(media(kind), prompt_extend=False), "需要 prompt_extend=true")
            self.assert_fail(request(media(kind, 2)), "数量 2 超过 1")
        self.assert_fail(request(media("file") + media("link")), "二选一")
        self.assert_pass(request(prompt_extend=False))

    def test_official_and_package_character_caps_are_separate(self):
        for length in (18000, 18001, 20000):
            req = request()
            req["input"]["prompt"] = "甲" * length
            self.assert_pass(req)
            if length == 18000:
                self.assert_pass(req, package=True)
            else:
                self.assert_fail(req, "本地制作包 18000", package=True)
        req["input"]["prompt"] = "甲" * 20001
        self.assert_fail(req, "官方 20000")

    def test_media_only_input_accepts_missing_or_blank_prompt(self):
        req = request(media("reference_image"))
        del req["input"]["prompt"]
        self.assert_pass(req)
        for value in ("", " \n\t "):
            req["input"]["prompt"] = value
            self.assert_pass(req)
            self.assert_pass(req, package=True)

    def test_prompt_or_valid_media_content_is_required(self):
        for inputs in ({}, {"prompt": ""}, {"prompt": " \n ", "media": []},
                       {"media": [{}]}, {"media": [{"type": "reference_image", "url": " "}]},
                       {"media": [{"type": "unknown", "url": "https://example.com/image"}]}):
            req = request()
            req["input"] = inputs
            self.assert_fail(req, "至少提供一项")
        result = self.assert_fail(
            {"model": "wan3.0-video", "input": {"media": [{"type": "reference_image", "url": " "}]}},
            ".url")
        self.assertTrue(any("至少提供一项" in error for error in result["errors"]))

    def test_nonstring_prompt_is_rejected_even_with_valid_media(self):
        for value in (None, 0, False, [], {}):
            req = request(media("reference_image"))
            req["input"]["prompt"] = value
            self.assert_fail(req, "提供时必须是字符串")

    def test_output_parameter_enums_and_booleans(self):
        for resolution in ("480P", "720P", "1080P"):
            self.assert_pass(request(resolution=resolution))
        for ratio in ("adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"):
            self.assert_pass(request(ratio=ratio, audio=False))
        self.assert_fail(request(resolution="4K"), "resolution")
        self.assert_fail(request(ratio="auto"), "ratio")
        self.assert_fail(request(audio=1), "audio")
        self.assert_fail(request(prompt_extend="true"), "prompt_extend")

    def test_structure_errors_are_reported_without_crashing(self):
        for req in (None, [], {}, {"model": "wrong", "input": []},
                    {"model": "wan3.0-video", "input": {"prompt": "x", "media": {}}, "parameters": []}):
            self.assertTrue(validator.check_request(req)["errors"])
        for item in (None, "url", {"type": []}, {"type": "imaginary", "url": "x"}):
            self.assertTrue(validator.check_request(request([item]))["errors"])
        self.assert_fail(request(media("reference_video")), "media_info 必须", [])

    def test_unknown_fields_are_explicitly_outside_scope(self):
        req = request(fps=24)
        req["input"]["asset_codes"] = ["CHAR_01"]
        result = self.assert_pass(req)
        self.assertTrue(any("fps" in warning for warning in result["warnings"]))
        self.assertTrue(any("asset_codes" in warning for warning in result["warnings"]))

    def test_check_does_not_mutate_inputs(self):
        req = request(media("reference_video"))
        info = {"0": {"duration_seconds": 5}}
        before = copy.deepcopy((req, info))
        self.assert_pass(req, info)
        self.assertEqual((req, info), before)

    def test_cli_reports_scope_and_sets_exit_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "request.json"
            metadata = Path(temporary) / "metadata.json"
            req = request(media("reference_video"))
            path.write_text(json.dumps(req), encoding="utf-8")
            metadata.write_text('{"0":{"duration_seconds":5}}', encoding="utf-8")
            base = [sys.executable, str(ROOT / "scripts" / "validate_wan30_request.py"), str(path)]
            success = subprocess.run(base + ["--media-info", str(metadata), "--package"], capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            result = json.loads(success.stdout)
            self.assertTrue(result["scope"]["video_duration_budget_verified"])
            failure = subprocess.run(base, capture_output=True, text=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("scope", json.loads(failure.stdout))
            path.write_text("invalid json", encoding="utf-8")
            bad_json = subprocess.run(base, capture_output=True, text=True)
            self.assertNotEqual(bad_json.returncode, 0)
            self.assertIn("scope", json.loads(bad_json.stdout))


if __name__ == "__main__":
    unittest.main()
