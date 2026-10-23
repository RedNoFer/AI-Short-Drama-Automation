#!/usr/bin/env python3
"""提示词分层检查的回归自测。

运行：python3 scripts/tests/test_prompt_layering.py
覆盖 validate_compact_package.py 的 check_prompt_layers：资产图写镜头/台词、
Wan3.0 三锚写面料/剪裁、视频硬亮线，以及场景/道具材质词成簇提醒。
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


def parsed(asset_prompt: str = "正常角色图片提示词。", video_prompt: str = "") -> dict:
    return {
        "assets": [{
            "code": "CHAR_01", "kind": "角色", "name": "娜琳",
            "prompt": asset_prompt,
        }],
        "episodes": [{
            "code": "E01",
            "shots": [{
                "code": "SH01",
                "bindings": {},
                "prompts": {"视频提示词": video_prompt},
            }],
        }],
    }


def run(data: dict, model: str = "wan30") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    validator.check_prompt_layers(
        data, {"CHAR_01": "娜琳 นลิน"}, POLICY, model, errors, warnings)
    return errors, warnings


class PromptLayeringTests(unittest.TestCase):
    def test_asset_prompt_rejects_camera_movement(self):
        errors, _ = run(parsed(asset_prompt="角色站在白底前，镜头缓慢推近，再硬切到背面。"))
        self.assertTrue(any("资产图只写外观" in e for e in errors), errors)

    def test_asset_prompt_rejects_dialogue(self):
        errors, _ = run(parsed(asset_prompt="角色正面站着，台词：你好，旁白：她来了。"))
        self.assertTrue(any("资产图只写外观" in e for e in errors), errors)

    def test_asset_prompt_negative_clause_is_not_flagged(self):
        errors, _ = run(parsed(asset_prompt="正面单人塑像。不要：硬切、推近、台词。"))
        self.assertEqual(errors, [])

    def test_wan30_anchor_rejects_material_and_cut(self):
        video = (
            "【公共总规范】【角色一致性】娜琳：黑色短发／细框眼镜／白色圆领衬衫。\n"
            "【时间轴】\n0-5秒，硬切，镜头：中景。"
        )
        errors, _ = run(parsed(video_prompt=video))
        self.assertTrue(any("三锚写了「圆领」" in e for e in errors), errors)

    def test_wan30_anchor_rejects_fabric(self):
        video = (
            "【公共总规范】【角色一致性】娜琳：黑色短发／细框眼镜／米色棉麻连衣裙。\n"
            "【时间轴】\n0-5秒，硬切，镜头：中景。"
        )
        errors, _ = run(parsed(video_prompt=video))
        self.assertTrue(any("三锚写了「棉麻」" in e for e in errors), errors)

    def test_wan30_anchor_clean_passes(self):
        video = (
            "【公共总规范】【角色一致性】娜琳：黑色短发／细框眼镜／白色T恤。\n"
            "【时间轴】\n0-5秒，硬切，镜头：中景。"
        )
        errors, _ = run(parsed(video_prompt=video))
        self.assertEqual(errors, [])

    def test_wan30_anchor_allows_garment_type(self):
        for top in ("黑色皮夹克", "米白色针织衫", "藏青夹克"):
            video = (
                f"【公共总规范】【角色一致性】娜琳：黑色短发／细框眼镜／{top}。\n"
                "【时间轴】\n0-5秒，硬切，镜头：中景。"
            )
            errors, _ = run(parsed(video_prompt=video))
            self.assertEqual(errors, [], top)

    def test_asset_prompt_negated_camera_word_passes(self):
        errors, _ = run(parsed(asset_prompt="正面单人塑像。画面无转场、无硬切；镜头固定平视。"))
        self.assertEqual(errors, [])

    def test_anchor_check_skips_non_wan30(self):
        video = (
            "【公共总规范】【角色一致性】娜琳：黑色短发／细框眼镜／白色圆领衬衫。\n"
            "【时间轴】\n0-5秒，硬切，镜头：中景。"
        )
        errors, _ = run(parsed(video_prompt=video), model="seedance25")
        self.assertEqual(errors, [])

    def test_video_rejects_hard_gloss(self):
        video = "【时间轴】\n0-5秒，硬切，镜头：全景。车身反出一条硬亮线。"
        errors, _ = run(parsed(video_prompt=video))
        self.assertTrue(any("硬亮线" in e for e in errors), errors)

    def test_video_negative_gloss_is_not_flagged(self):
        video = "【时间轴】\n0-5秒，硬切，镜头：全景。高光柔和，不形成硬亮线。"
        errors, _ = run(parsed(video_prompt=video))
        self.assertEqual(errors, [])

    def test_scene_detail_cluster_warns(self):
        video = "【时间轴】\n0-5秒，硬切，镜头：全景。墙面斑驳、木纹清楚、青苔沿砖缝长。"
        errors, warnings = run(parsed(video_prompt=video))
        self.assertEqual(errors, [])
        self.assertTrue(any("场景材质/纹理" in w for w in warnings), warnings)

    def test_prop_detail_cluster_warns(self):
        video = "【时间轴】\n0-5秒，硬切，镜头：特写。金属边、塑料壳、皮革带都入画。"
        errors, warnings = run(parsed(video_prompt=video))
        self.assertEqual(errors, [])
        self.assertTrue(any("道具材质/形制" in w for w in warnings), warnings)

    def test_generic_style_line_is_not_a_cluster(self):
        video = (
            "【公共总规范】真人现实主义电影摄影；物理光照；实物材质与使用痕迹可辨。\n"
            "【时间轴】\n0-5秒，硬切，镜头：中景。"
        )
        _, warnings = run(parsed(video_prompt=video))
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
