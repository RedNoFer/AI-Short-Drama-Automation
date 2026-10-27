#!/usr/bin/env python3
"""validate_compact_package.py 的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_compact_validator.py
新增/修改校验规则时先跑本测试；PROC-02 记录过校验器自身回归。
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
_validate_api = validator.validate


def _validate_seedance_for_legacy_fixtures(source: str, policy: dict, *args, **kwargs):
    """这些旧夹具是 Seedance 样本；显式登记轨，避免测试夹具继续依赖隐式默认。"""
    kwargs.setdefault("model", "seedance25")
    return _validate_api(source, policy, *args, **kwargs)


validator.validate = _validate_seedance_for_legacy_fixtures

HEADER = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜阿泽

#### 图片提示词

```text
生成16:9横版角色资产图：单张、单人全身正面塑像式基准图，身体正对镜头、双眼平视，人物占画面高度92%–94%，中性浅灰无缝背景，黑色碎短发、左手腕旧手绳、深灰机能外套，深灰工装裤与深色徒步鞋，不作四视图、不作多视图拼版。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
```
"""

EPISODE_TMPL = """## 剧集 {ep}｜测试集{n}

### 小说原文

```text
第{n}集的小说原文。
```

### 片段 {sh}｜{dur}秒｜测试片段{n}{suffix}

角色：CHAR_01
场景：LOC_01

#### 视频提示词

```text
【参考】CHAR_01=阿泽外观锁定；LOC_01=起点路段。
【公共总规范】统一3D国漫画风。【角色一致性】阿泽：黑色碎短发／左手腕旧手绳／深灰机能外套。{pad}{lock}
【时间轴】
{rows}
【收尾】阿泽走远，下一片段承接。
```
"""

GOOD_ROWS = "\n".join([
    '0-5秒，阿泽站在雨里，镜头平视不动，他作口型对白、口型同步，说："你好。"',
    '5-10秒，硬切，风吹过路面，他侧头听声。',
    '10-15秒，硬切，远处雾里有光，他向前一步。',
    '15-20秒，硬切，他停住脚步，眉头收紧。',
    '20-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
])

LOCK = "声线锁定：CHAR_01＝26岁男声，中低音清冷略沙。"


def make_package(*, lock: str = LOCK, rows: str | None = None,
                 include_param: bool = False, second_episode: bool = False,
                 second_lock: str | None = None, title_suffix: str = "",
                 dur: int = 30, pad: str = "", ratio: str = "16:9") -> str:
    """ratio 按轨给：Seedance/H3 四视图＝16:9；Wan3.0 塑像图＝9:16（2026-10-25 定版）。"""
    rows = (rows or GOOD_ROWS).format(ep="E01", sh="SH01")
    first = EPISODE_TMPL.format(ep="E01", sh="SH01", n=1, lock=lock, rows=rows,
                                suffix=title_suffix, dur=dur, pad=pad)
    if include_param:
        first = first.replace("【参考】", "【参数】剧集E01片段SH01；30秒。\n【参考】", 1)
    body = HEADER + first
    if second_episode:
        rows2 = GOOD_ROWS.format(ep="E02", sh="SH01")
        body += EPISODE_TMPL.format(ep="E02", sh="SH01", n=2, lock=second_lock or lock, rows=rows2, suffix="", dur=dur, pad=pad)
    if ratio != "16:9":
        body = body.replace("生成16:9横版角色资产图", f"生成{ratio}竖版角色资产图")
    return body


ONER_ROWS = "\n".join([
    '0-4秒，狼群自雾中压低身躯围拢，镜头贴地跟移，阿泽横刀立定，刀刃映出绿光。',
    '4-14秒，镜头不停，随他侧身滑步绕行，狼影扑至时他拧腰格挡、刀背磕开兽爪，借冲力翻身换位，焦点在兽瞳与刀刃之间快速切换，雾气被劲风撕开一道口子。',
    '14-24秒，镜头随他蹬地跃起升至高位俯瞰，狼群合围成环，他落回圈内以攻代守，刀光连成弧面，每一记挥砍都逼得最近的狼影后撤半步。',
    '24-30秒，镜头缓缓拉远升高，一人一环狼对峙于雾心，他收刀入鞘，绿光在雾里明灭。',
])

# ONER_ROWS / WAN_ROWS 是**无台词**夹具（打斗、时长、五人锁定），按 CAST-04
# 「声线锁定只列本段实际发声者」，这些用例一律传 lock=""；
# 要测声线锁定本身请用 GOOD_ROWS（含口型对白），见 test_dialogue_without_voice_lock_rejected。
WAN_ROWS = "\n".join([
    '0-1.5秒，阿泽立在零公里路牌下，晨雾漫过路面，镜头贴地缓升。',
    '1.5-4秒，硬切，牛皮纸包裹特写，绳结与纸纹清晰可辨。',
    '4-9秒，硬切，他拆开包装，泛黄古图徐徐展开，镜头缓推。',
    '9-14.5秒，硬切，字条特写，他瞳孔微收，指节泛白。',
    '14.5-22秒，硬切，五人围拢，焦点在字迹与面孔之间缓慢转换。本镜画面内恰好五人：左起阿泽、苏晚、老杨、许棠、小林；每人只有一个身体、一张脸；不出现第六人。',
    '22-30秒，硬切，古图边缘银纹微亮，他收图入怀，雾从车头漫过。',
])

WAN_PAD = "一致性枚举：阿泽碎短发垂额、深灰冲锋衣、左手腕旧手绳全程佩戴；" * 260


class CompactValidatorTests(unittest.TestCase):
    def test_space_timecode_accepts_unicode_dash_and_seconds_suffix(self):
        parsed = validator.parse_structure(make_package(rows=GOOD_ROWS))
        with tempfile.TemporaryDirectory() as d:
            space_dir = Path(d)
            (space_dir / "E01_SH01_S01.json").write_text(json.dumps({
                "shot": "E01_SH01_S01", "timecode": "0–5秒", "characters": [],
                "camera": {},
            }, ensure_ascii=False), encoding="utf-8")
            errors, _, stats = validator.check_space_sync(
                parsed, {"CHAR_01": "阿泽"}, space_dir, "seedance25")
        self.assertEqual(errors, [])
        self.assertEqual(stats["coverage"]["E01/SH01"], "1/6")

    def test_python_api_fails_closed_without_model_or_manifest(self):
        result = _validate_api(make_package(), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("未能确认唯一有效模型轨" in e for e in result["errors"]), result["errors"])

    def test_python_api_reads_registered_model_from_source_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            internal = root / "内部"
            internal.mkdir()
            (internal / "00-项目输入单.md").write_text(
                "# 项目输入单\n\n| 生成轨 | wan30 |\n", encoding="utf-8")
            source_file = root / "精简制作包.md"
            result = _validate_api(
                make_package(ratio="9:16", rows=WAN_ROWS, lock=""), POLICY,
                source_file=source_file, space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["model"], "wan30")

    def test_check_prompt_fails_closed_without_model(self):
        errors = []
        validator.check_prompt("", "E01", "SH01", 30, {}, POLICY, errors)
        self.assertTrue(any("必须收到显式有效模型轨" in e for e in errors), errors)

    def test_good_package_passes(self):
        result = validator.validate(make_package(), POLICY)
        self.assertTrue(result["ok"], result["errors"])

    def test_custom_asset_section_and_explanatory_text_are_rejected(self):
        for extra in ("## 二、移动道具与可穿戴资产图片提示词", "以下均为内部资产制作说明。"):
            with self.subTest(extra=extra):
                pkg = make_package().replace("## 固定资产", "## 固定资产\n\n" + extra, 1)
                result = validator.validate(pkg, POLICY)
                self.assertFalse(result["ok"])
                self.assertTrue(any("无法识别" in e for e in result["errors"]), result["errors"])

    def test_wide_single_empty_scene_is_accepted_as_panorama(self):
        """阶段2写法「16:9横版单张空镜」与全景底板语义一致，不要求重复塞入“全景”。"""
        pkg = make_package().replace("16:9横版单张全景基准图", "16:9横版单张空镜基准图")
        result = validator.validate(pkg, POLICY, space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_scene_negative_movable_list_is_not_treated_as_positive(self):
        prompt = (
            "真实现场照片，低饱和。16:9横版单张空镜。画面中无人物；"
            "不出现车辆、动物与手持道具。本卡是场景底板，只锁空间、光位与材质。"
        )
        errors, warnings = [], []
        validator.check_scene_plate(
            [{"kind": "场景", "code": "LOC_01", "prompt": prompt}], errors, warnings, POLICY)
        self.assertEqual(errors, [])

    def test_scene_positive_vehicle_is_still_rejected(self):
        prompt = (
            "真实现场照片，低饱和。16:9横版单张空镜。画面中无人物，"
            "路边停着一辆轿车。本卡是场景底板，只锁空间、光位与材质。"
        )
        errors, warnings = [], []
        validator.check_scene_plate(
            [{"kind": "场景", "code": "LOC_01", "prompt": prompt}], errors, warnings, POLICY)
        self.assertTrue(any("可移动道具" in error for error in errors), errors)

    def test_param_section_rejected(self):
        result = validator.validate(make_package(include_param=True), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("【参数】" in e for e in result["errors"]))

    def test_procedural_row_rejected(self):
        bad_rows = GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "硬切，风吹过路面，他侧头听声。",
            "硬切，中景以侧45°固定机位拍下，他侧头听声。", 1)
        result = validator.validate(make_package(rows=bad_rows), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("程序性" in e or "景别参数开场" in e for e in result["errors"]))

    def test_dialogue_without_voice_lock_rejected(self):
        result = validator.validate(make_package(lock=""), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("声线锁定" in e for e in result["errors"]))

    def test_voice_lock_drift_across_episodes_rejected(self):
        drifted = "声线锁定：CHAR_01＝高亢尖细的少年音。"
        result = validator.validate(make_package(second_episode=True, second_lock=drifted), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("声线锁定跨片段不一致" in e for e in result["errors"]))

    def test_identical_voice_lock_across_episodes_passes(self):
        result = validator.validate(make_package(second_episode=True), POLICY)
        self.assertTrue(result["ok"], result["errors"])



    def test_legacy_shot_marker_rejected(self):
        legacy_rows = GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "5-10秒，硬切，风吹过路面",
            "5-10秒｜镜头 E01-SH01-S02｜硬切｜风吹过路面", 1)
        result = validator.validate(make_package(rows=legacy_rows), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("镜头项目编号" in e or "起始/硬切" in e for e in result["errors"]))

    def test_missing_natural_cut_word_rejected(self):
        no_cut = GOOD_ROWS.format(ep="E01", sh="SH01").replace("10-15秒，硬切，", "10-15秒，", 1)
        result = validator.validate(make_package(rows=no_cut), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("硬切" in e for e in result["errors"]))

    def test_fight_oner_passes(self):
        result = validator.validate(
            make_package(rows=ONER_ROWS, title_suffix="·一镜到底", lock=""), POLICY)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["mode"], "fight_oner")

    def test_fight_oner_hard_cut_rejected(self):
        bad = ONER_ROWS.replace("14-24秒，镜头随他蹬地跃起", "14-24秒，硬切，镜头随他蹬地跃起", 1)
        result = validator.validate(make_package(rows=bad, title_suffix="·一镜到底"), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("一镜到底" in e for e in result["errors"]))

    def test_fight_oner_rows_missing_transitions_still_needs_beats(self):
        single = '0-30秒，一镜打完，中间毫无节拍。'
        result = validator.validate(make_package(rows=single, title_suffix="·一镜到底"), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("拍点行" in e for e in result["errors"]))

    def test_wan30_decimal_and_long_prompt_passes(self):
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["model"], "wan30")
        # 同一包在 Seedance 轨下必须失败（小数行 + 超 3000 字符）
        bad = validator.validate(pkg, POLICY, space_exempt=True)
        self.assertFalse(bad["ok"])

    def test_wan30_short_complete_prompt_has_no_length_floor(self):
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, lock="")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertLess(result["stats"][0]["characters"], 1000)
        self.assertFalse(any("过简" in w or "目标带" in w for w in result["warnings"]))

    def test_wan30_requires_registered_9_16_character_asset(self):
        """Wan3.0 角色卡必须写 9:16（policy.assets.wan30_character_ratio）；写 16:9 判错。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
        pkg = pkg.replace("生成9:16竖版角色资产图", "生成16:9横版角色资产图", 1)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("必须明确写 9:16" in e for e in result["errors"]))

    def test_wan30_statue_without_single_card_word_does_not_hit_generic_four_view_gate(self):
        """Wan checks its statue profile directly; Seedance/H3 single-still gate must not run first."""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
        pkg = pkg.replace("单张、单人全身正面塑像式", "单人全身正面塑像式", 1)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_wan30_missing_single_person_gets_wan_specific_diagnostic(self):
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
        pkg = pkg.replace("单张、单人全身正面塑像式", "单张、成年角色全身正面塑像式", 1)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Wan3.0 轨角色资产图必须是单人塑像图" in e for e in result["errors"]))
        self.assertFalse(any("缺少默认四视图版式" in e for e in result["errors"]))

    def test_wan30_one_take_does_not_inherit_seedance_4500_cap(self):
        rows = "\n".join([
            "0-15秒，镜头环绕人物，角色先压低重心再向前跨步，",
            "15-30秒，镜头继续跟随，角色侧身停步并回头确认来路。",
        ])
        pkg = make_package(ratio="9:16", rows=rows, pad=WAN_PAD, lock="", title_suffix="·一镜到底")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertGreater(result["stats"][0]["characters"], 4500)

    def test_cli_infers_wan_branch_and_rejects_seedance_override(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            internal = project / "内部"
            internal.mkdir()
            (internal / "00-项目输入单.md").write_text(
                "| 生成轨 | wan30 |\n", encoding="utf-8")
            package = project / "精简制作包.md"
            package.write_text(
                make_package(ratio="9:16", rows=GOOD_ROWS, pad=WAN_PAD), encoding="utf-8")
            script = ROOT / "scripts" / "validate_compact_package.py"
            inferred = subprocess.run(
                [sys.executable, str(script), str(package)],
                capture_output=True, text=True)
            self.assertEqual(inferred.returncode, 0, inferred.stdout + inferred.stderr)
            mismatch = subprocess.run(
                [sys.executable, str(script), str(package), "--model", "seedance25"],
                capture_output=True, text=True)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("模型轨不匹配", mismatch.stderr)

    def test_cli_rejects_unreadable_or_duplicate_branch_registration(self):
        """输入单存在但登记值不合法/不唯一时，绝不静默退回 Seedance。"""
        for registration in (
            "| 生成轨 | Wan3.0 |\n",
            "| 生成轨 | wan30 |\n| 生成轨 | seedance25 |\n",
        ):
            with self.subTest(registration=registration), tempfile.TemporaryDirectory() as temp:
                project = Path(temp)
                internal = project / "内部"
                internal.mkdir()
                (internal / "00-项目输入单.md").write_text(registration, encoding="utf-8")
                package = project / "精简制作包.md"
                package.write_text(make_package(rows=GOOD_ROWS), encoding="utf-8")
                script = ROOT / "scripts" / "validate_compact_package.py"
                result = subprocess.run(
                    [sys.executable, str(script), str(package)],
                    capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("必须且只能有一个有效登记值", result.stderr)

    def test_cli_without_manifest_requires_explicit_model(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            package = project / "精简制作包.md"
            package.write_text(make_package(rows=GOOD_ROWS), encoding="utf-8")
            script = ROOT / "scripts" / "validate_compact_package.py"
            implicit = subprocess.run(
                [sys.executable, str(script), str(package)],
                capture_output=True, text=True)
            self.assertNotEqual(implicit.returncode, 0)
            self.assertIn("未找到输入单生成轨", implicit.stderr)
            explicit = subprocess.run(
                [sys.executable, str(script), str(package), "--model", "seedance25"],
                capture_output=True, text=True)
            self.assertEqual(explicit.returncode, 0, explicit.stdout + explicit.stderr)

    def test_wan30_asset_requires_front_and_height_in_92_94_range(self):
        base = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
        result = validator.validate(base, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

        for bad in ("占画面高度90%", "占画面高度95%", "占画面高度90%–95%"):
            with self.subTest(bad=bad):
                pkg = base.replace("人物占画面高度92%–94%", f"人物{bad}")
                result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
                self.assertFalse(result["ok"])
                self.assertTrue(any("占画面高度须为 92%–94%" in e for e in result["errors"]))

        no_front = base.replace("全身正面塑像式", "全身塑像式")
        result = validator.validate(no_front, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("正面视角" in e for e in result["errors"]))

    def test_wan30_prompt_has_only_inclusive_hard_cap(self):
        """短稿、旧目标带两侧及18000/18001边界只按硬上限判断长度。"""
        base = make_package(ratio="9:16", rows=WAN_ROWS, pad="", lock="")
        prompt_len = len(
            validator.parse_structure(base)["episodes"][0]["shots"][0]["prompts"]["视频提示词"])
        # Padding is synthetic boundary-test input, never production prompt guidance.
        for length in (prompt_len, 1000, 7999, 8000, 15000, 15001, 17999, 18000, 18001):
            with self.subTest(length=length):
                pad = "甲" * (length - prompt_len)
                result = validator.validate(
                    make_package(ratio="9:16", rows=WAN_ROWS, pad=pad, lock=""), POLICY,
                    model="wan30", space_exempt=True)
                self.assertEqual(result["stats"][0]["characters"], length)
                self.assertFalse(any("目标带" in w or "过简" in w for w in result["warnings"]),
                                 result["warnings"])
                if length <= 18000:
                    self.assertTrue(result["ok"], result["errors"])
                else:
                    self.assertFalse(result["ok"])
                    self.assertTrue(any("超过 18000 硬顶" in e for e in result["errors"]), result["errors"])

    def test_wan30_legacy_target_hints_do_not_restore_floor(self):
        policy = json.loads(json.dumps(POLICY))
        policy["model_profiles"]["wan30"].update(
            prompt_target_min_chars=8000, prompt_target_max_chars=15000)
        result = validator.validate(
            make_package(ratio="9:16", rows=WAN_ROWS, lock=""), policy,
            model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_wan30_empty_prompt_is_still_rejected(self):
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, lock="")
        prompt = validator.parse_structure(pkg)["episodes"][0]["shots"][0]["prompts"]["视频提示词"]
        result = validator.validate(pkg.replace(prompt, ""), POLICY,
                                    model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("缺少视频提示词" in e for e in result["errors"]), result["errors"])

    def test_wan30_missing_ratio_policy_fails_closed(self):
        policy = json.loads(json.dumps(POLICY))
        policy["assets"].pop("wan30_character_ratio", None)
        result = validator.validate(
            make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock=""), policy,
            model="wan30", space_exempt=True)
        self.assertTrue(any("wan30_character_ratio 未配置" in e for e in result["errors"]), result["errors"])

    def test_wan30_missing_length_profile_fails_closed(self):
        """Wan字数策略缺项时必须拒绝回退到Seedance的3000字符配置。"""
        for cap in (None, 0, -1, True, "18000"):
            with self.subTest(invalid_cap=cap):
                policy = json.loads(json.dumps(POLICY))
                policy["model_profiles"]["wan30"]["prompt_max_chars"] = cap
                result = validator.validate(
                    make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock=""), policy,
                    model="wan30", space_exempt=True)
                self.assertFalse(result["ok"])
                self.assertTrue(any("缺少 Wan3.0 字数 profile" in e for e in result["errors"]),
                                result["errors"])

    def test_tier_is_rejected_outside_seedance_branch(self):
        result = validator.validate(
            make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock=""), POLICY,
            model="wan30", tier="tier2_xiaomo63", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("--tier 仅适用于 Seedance 2.5" in e for e in result["errors"]),
                        result["errors"])

    def test_group_shot_requires_headcount_lock(self):
        """四人以上同框必须写人数锁定句（WAN30-02 第 3 条）。"""
        rows = WAN_ROWS.replace(
            "本镜画面内恰好五人：左起阿泽、苏晚、老杨、许棠、小林；"
            "每人只有一个身体、一张脸；不出现第六人。", "")
        pkg = make_package(ratio="9:16", rows=rows, pad=WAN_PAD)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("人数锁定句" in e for e in result["errors"]), result["errors"])

    def test_five_person_lock_may_name_only_three(self):
        """五人锁定句允许只点名三人、另两人按服装特征定位（2026-10-22 裁决）。"""
        rows = WAN_ROWS.replace(
            "本镜画面内恰好五人：左起阿泽、苏晚、老杨、许棠、小林；"
            "每人只有一个身体、一张脸；不出现第六人。",
            "本镜画面内恰好五人：左起苏晚、老杨、阿泽、黑色机能马甲的年轻女性、亮蓝防风外套的少年；"
            "每人只有一个身体、一张脸；不出现第六人。")
        pkg = make_package(ratio="9:16", rows=rows, pad=WAN_PAD, lock="")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_first_beat_must_not_write_hard_cut(self):
        """首拍不得写「硬切」——首镜直写开场，硬切只用于其后每一拍。"""
        rows = WAN_ROWS.replace("0-1.5秒，阿泽立在", "0-1.5秒，硬切，阿泽立在", 1)
        pkg = make_package(ratio="9:16", rows=rows, pad=WAN_PAD)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("首拍不得写" in e for e in result["errors"]), result["errors"])

    def test_public_shot_count_declaration_must_match(self):
        """公共总规范自报的「全段 N 拍 M 次硬切」须与正文一致。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD)
        pkg = pkg.replace("【公共总规范】", "【公共总规范】全段 9 拍 8 次硬切；", 1)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("与正文不符" in e for e in result["errors"]), result["errors"])

    def test_wan30_duration_bounds(self):
        rows24 = WAN_ROWS.replace("14.5-22秒", "14.5-20秒").replace("22-30秒", "20-24秒")
        pkg = make_package(ratio="9:16", rows=rows24, pad=WAN_PAD, dur=24, lock="")
        self.assertTrue(validator.validate(pkg, POLICY, model="wan30", space_exempt=True)["ok"])
        self.assertFalse(validator.validate(pkg, POLICY, space_exempt=True)["ok"])

    def test_wan30_granularity_rejected(self):
        bad_rows = WAN_ROWS.replace("1.5-4秒", "1.7-4秒", 1)
        result = validator.validate(make_package(ratio="9:16", rows=bad_rows, pad=WAN_PAD), POLICY, model="wan30")
        self.assertFalse(result["ok"])
        self.assertTrue(any("0.5 秒" in e for e in result["errors"]))


    def test_smile_risk_word_without_qualifier_rejected(self):
        risky = GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "硬切，风吹过路面，他侧头听声。",
            "硬切，风吹过路面，他勉强挤出苦笑。", 1)
        result = validator.validate(make_package(rows=risky), POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("演成微笑" in e for e in result["errors"]))

    def test_smile_risk_word_with_qualifier_passes(self):
        safe = GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "硬切，风吹过路面，他侧头听声。",
            "硬切，风吹过路面，他嘴角不上扬，不出现微笑。", 1)
        result = validator.validate(make_package(rows=safe), POLICY)
        self.assertTrue(result["ok"], result["errors"])


    def test_watch_word_warns_but_passes(self):
        watch = GOOD_ROWS.format(ep="E01", sh="SH01").replace(
            "硬切，风吹过路面，他侧头听声。",
            "硬切，风吹过路面，他语气释然。", 1)
        result = validator.validate(make_package(rows=watch), POLICY)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(any("需判定" in w for w in result.get("warnings", [])))

def make_sequel(*, ep: str = "E02", char_name: str = "阿泽", char_code: str = "CHAR_01",
                char_prompt: str | None = None, extra_asset: str = "") -> str:
    """Build a sequel package that is checked against a baseline package."""
    header = HEADER
    if char_name != "阿泽" or char_code != "CHAR_01":
        header = header.replace("### 角色 CHAR_01｜阿泽", f"### 角色 {char_code}｜{char_name}")
    if char_prompt is not None:
        header = re.sub(
            r"(### 角色 CHAR_01｜阿泽\n\n#### 图片提示词\n\n```text\n).*?(\n```)",
            lambda match: match.group(1) + char_prompt + match.group(2),
            header, flags=re.S)
    if extra_asset:
        header = header.replace("## 固定资产\n", "## 固定资产\n\n" + extra_asset, 1)
    episode = EPISODE_TMPL.format(ep=ep, sh="SH01", n=2, lock=LOCK, rows=GOOD_ROWS,
                                   suffix="", dur=30, pad="")
    return header + episode


class SequelValidatorTests(unittest.TestCase):
    """续集校验：集代码归属、资产名称对齐与代码冲突。"""

    def test_clean_sequel_passes(self):
        baseline = make_package()
        result = validator.validate(make_sequel(), POLICY, baseline=baseline)
        self.assertTrue(result["ok"], result["errors"])

    def test_sequel_reusing_existing_episode_code_rejected(self):
        baseline = make_package()
        result = validator.validate(make_sequel(ep="E01"), POLICY, baseline=baseline)
        self.assertFalse(result["ok"])
        self.assertTrue(any("整集替换" in e for e in result["errors"]))

    def test_sequel_renamed_asset_rejected(self):
        baseline = make_package()
        result = validator.validate(make_sequel(char_name="阿泽（续集）"), POLICY, baseline=baseline)
        self.assertFalse(result["ok"])
        self.assertTrue(any("名称须与项目已有资产逐字一致" in e for e in result["errors"]))

    def test_sequel_same_name_new_code_rejected(self):
        baseline = make_package()
        clone = ("### 角色 CHAR_09｜阿泽\n\n#### 图片提示词\n\n"
                 "```text\n生成16:9横版白底角色四视图设定图。\n```\n\n")
        result = validator.validate(make_sequel(extra_asset=clone), POLICY, baseline=baseline)
        self.assertFalse(result["ok"])
        self.assertTrue(any("请沿用 CHAR_01" in e for e in result["errors"]))

    def test_sequel_reused_asset_blank_prompt_only_warns(self):
        baseline = make_package()
        result = validator.validate(make_sequel(char_prompt=""), POLICY, baseline=baseline)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(any("图片提示词留空" in w for w in result.get("warnings", [])))

    def test_sequel_episode_number_should_follow_baseline(self):
        baseline = make_package(second_episode=True)
        result = validator.validate(make_sequel(ep="E02"), POLICY, baseline=baseline)
        self.assertTrue(any("集号不大于基线包最大集号" in w for w in result.get("warnings", [])))

    def test_second_character_card_with_variant_suffix_rejected(self):
        """一人一卡：同一角色的 CHAR_0X_PHOTO 变体会被导入端当成新角色。"""
        clone = ("### 角色 CHAR_01_PHOTO｜阿泽（剧照）\n\n#### 图片提示词\n\n"
                 "```text\n生成16:9横版单张电影剧照，单人入画。\n```\n\n")
        pkg = make_package().replace("### 场景 LOC_01", clone + "### 场景 LOC_01", 1)
        result = validator.validate(pkg, POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("同一角色的第二张卡" in e for e in result["errors"]))

    def test_single_still_character_card_passes_layout_check(self):
        """一人一卡的单张剧照版式必须被认作合法角色版式。"""
        pkg = make_package().replace(
            "生成16:9横版角色资产图：单张、单人全身塑像式基准图，中性浅灰无缝背景，黑色碎短发、左手腕旧手绳、深灰机能外套，深灰工装裤与深色徒步鞋，不作四视图、不作多视图拼版。",
            "生成16:9横版单张电影剧照，单人入画，3/4 侧身。")
        result = validator.validate(pkg, POLICY)
        self.assertTrue(result["ok"], result["errors"])


    def test_wan30_package_rejects_inline_image_numbers(self):
        """WAN30-04：包内不得写 @ImageN——编号由应用按上传顺序生成。"""
        prompt = (
            "【参考】@Image1＝CHAR_01；@Image2＝CHAR_02\n"
            "【公共总规范】全段1拍0次硬切。阿泽（@Image1）：黑色碎短发。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01", "CHAR_02"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽", "CHAR_02": "苏晚"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01", "CHAR_02"}, asset_prompts={})
        self.assertTrue(any("WAN30-04" in e for e in errors), errors)

    def test_wan30_name_only_reference_passes(self):
        """改用资产名称点名后不再报 WAN30-04。"""
        prompt = (
            "【参考】CHAR_01＝身份与服装唯一基准；CHAR_02＝身份与服装唯一基准。\n"
            "【公共总规范】全段1拍0次硬切。阿泽：黑色碎短发／左手腕旧手绳／深灰机能外套。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01", "CHAR_02"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽", "CHAR_02": "苏晚"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01", "CHAR_02"}, asset_prompts={})
        self.assertFalse(any("WAN30-04" in e for e in errors), errors)

    def test_wan30_character_asset_must_be_single_statue(self):
        """Wan3.0 角色资产图必须是单人塑像单张，不得四视图拼版。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="").replace(
            "生成9:16竖版角色资产图：单张、单人全身正面塑像式基准图，身体正对镜头、双眼平视，人物占画面高度92%–94%，中性浅灰无缝背景，黑色碎短发、左手腕旧手绳、深灰机能外套，深灰工装裤与深色徒步鞋，不作四视图、不作多视图拼版。",
            "生成16:9横版白底角色四视图设定图。")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("单人塑像" in e for e in result["errors"]), result["errors"])

    def test_wan30_single_still_without_statue_shape_is_rejected(self):
        """只写单张剧照仍不是Wan要求的单人全身塑像图。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="").replace(
            "单张、单人全身正面塑像式基准图", "单张、单人全身正面角色照片")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(any("须明确为塑像图" in e for e in result["errors"]), result["errors"])

    def test_wan30_half_body_asset_rejected(self):
        """半身资产图锁不住下装与鞋，Wan3.0 判错。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="").replace(
            "单张、单人全身正面塑像式基准图", "单张、单人半身正面塑像式基准图")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("全身入画" in e for e in result["errors"]), result["errors"])

    def test_wan30_asset_requires_lower_body_and_shoes(self):
        """全身塑像必须写下装与鞋，否则成片逐镜换裤换鞋。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD).replace(
            "深灰工装裤与深色徒步鞋", "")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("下装" in e for e in result["errors"]), result["errors"])
        self.assertTrue(any("鞋" in e for e in result["errors"]), result["errors"])

    def test_wan30_anchor_mismatch_rejected(self):
        """正文三锚与资产图不同源（词说裙子、图是工装裤）判错。"""
        prompt = (
            "【参考】CHAR_01＝身份与服装唯一基准（单人塑像图，全片不变）。\n"
            "【公共总规范】全段1拍0次硬切。阿泽：栗色长卷发／米色半身裙／白色风衣。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01"},
            asset_prompts={"CHAR_01": "黑色碎短发，深灰工装裤，深色徒步鞋。"})
        self.assertTrue(any("不同源" in e for e in errors), errors)

    def test_wan30_deny_reference_rejected(self):
        """WAN30-05：把资产图降级成「只作比对、不作视频参考」等于放弃图锚。"""
        prompt = (
            "【参考】CHAR_01＝身份与体态基准，资产卡只作身份与服化比对，不作视频参考帧。\n"
            "【公共总规范】全段1拍0次硬切。阿泽：黑色碎短发／左手腕旧手绳／深灰机能外套。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01"}, asset_prompts={})
        self.assertTrue(any("WAN30-05" in e for e in errors), errors)

    def test_wan30_four_view_card_in_reference_rejected(self):
        """WAN30-05：参考里仍写「资产卡为四视图」与单人塑像图互斥。"""
        prompt = (
            "【参考】CHAR_01＝身份与服装唯一基准，资产卡为 16:9 白底四视图设定板。\n"
            "【公共总规范】全段1拍0次硬切。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01"}, asset_prompts={})
        self.assertTrue(any("WAN30-05" in e for e in errors), errors)

    def test_duplicate_outfit_variant_rejected(self):
        """服装变体与默认装同款＝同一套衣服登记两次，模型会当成两套来回切。"""
        pkg = make_package().replace(
            "### 场景 LOC_01｜起点",
            "### 道具 PROP_01｜阿泽·深灰西装\n\n#### 图片提示词\n\n"
            "```text\n生成16:9横版单张服装变体设定板，本套装供 CHAR_01 穿着，与角色默认装同款。\n```\n\n"
            "### 场景 LOC_01｜起点")
        result = validator.validate(pkg, POLICY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("同款" in e for e in result["errors"]), result["errors"])

    def test_wan30_missing_three_anchors_rejected(self):
        """WAN30-06：绑定角色没有三锚条款，远景全身会脱离参考图。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD).replace(
            "【角色一致性】阿泽：黑色碎短发／左手腕旧手绳／深灰机能外套。", "")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("WAN30-06" in e for e in result["errors"]), result["errors"])

    def test_wan30_asset_rejects_side_gaze_and_three_quarter(self):
        """资产卡写「不看镜头」或「3/4」会把人拍成斜侧面，锁脸变弱。"""
        for bad in ("不看镜头", "3/4 站立", "占画面高度约 85%"):
            pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD, lock="")
            if bad.startswith("占画面高度"):
                pkg = pkg.replace("人物占画面高度92%–94%", f"人物{bad}")
            else:
                pkg = pkg.replace("深灰工装裤与深色徒步鞋，", f"深灰工装裤与深色徒步鞋，{bad}，")
            result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
            self.assertFalse(result["ok"], bad)
            marker = "占画面高度" if bad.startswith("占画面高度") else "资产卡"
            self.assertTrue(any(marker in e for e in result["errors"]), (bad, result["errors"]))

    def test_wan30_asset_negative_list_must_not_ban_camera_gaze(self):
        """负向写「看镜头」会抵消正面要求，把人推回侧脸。"""
        pkg = make_package(ratio="9:16", rows=WAN_ROWS, pad=WAN_PAD).replace(
            "深灰工装裤与深色徒步鞋，", "深灰工装裤与深色徒步鞋，负向限制：侧身、看镜头、磨皮，")
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("负向清单" in e for e in result["errors"]), result["errors"])

    def test_wan30_reference_must_not_repeat_asset_name(self):
        """代码后重复名称会被应用渲染成「娜琳 娜琳＝…」，可能被读成两个人。"""
        prompt = (
            "【参考】CHAR_01 阿泽＝身份与服装唯一基准（单人塑像图，全片不变）。\n"
            "【公共总规范】全段1拍0次硬切。阿泽：黑色碎短发／左手腕旧手绳／深灰机能外套。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01"}, asset_prompts={})
        self.assertTrue(any("重复写了名称" in e for e in errors), errors)

    def test_normative_docs_have_no_stale_wan30_patterns(self):
        """规范文档不得再写回旧口径：参考行重复名称、正面 3/4 资产卡。"""
        repo = ROOT.parents[2]
        docs = [repo / "AGENTS.md"] + [
            p for p in ROOT.rglob("*.md")
            if p.name != "failure-cases.md"]  # 案例表会引用历史错误写法
        hits = []
        for doc in docs:
            for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
                if "渲染成" in line or "旧写法" in line:
                    continue
                if re.search(r"(?:CHAR|LOC|PROP)_\d+[ \u3000]+[^＝；，\n]{1,24}＝", line):
                    hits.append(f"{doc.name}:{lineno} 参考行重复名称")
                if re.search(r"正面\s*3/4\s*站立|正面或\s*3/4", line):
                    hits.append(f"{doc.name}:{lineno} 旧 3/4 资产卡口径")
        self.assertEqual(hits, [], "规范文档残留旧口径：" + "; ".join(hits[:6]))

    def test_reference_ledger_off_by_one_rejected(self):
        """WAN30-03：参考清单按上传顺序编号，正文 @ImageN 必须同序同人。"""
        prompt = (
            "【参考图片】：\n"
            "@图片1：场景「成都 318 零公里路牌」\n"
            "@图片2：角色「阿泽」\n"
            "@图片3：角色「苏晚」\n\n"
            "【参考】@Image1＝CHAR_01；@Image2＝CHAR_02\n"
            "【公共总规范】全段1拍0次硬切。阿泽（@Image1）：黑色碎短发。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01", "CHAR_02"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽", "CHAR_02": "苏晚"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01", "CHAR_02"}, asset_prompts={})
        self.assertTrue(any("WAN30-03" in e for e in errors), errors)

    def test_reference_ledger_aligned_passes(self):
        """清单与正文同序时不报 WAN30-03。"""
        prompt = (
            "【参考图片】：\n"
            "@图片1：角色「阿泽」\n"
            "@图片2：角色「苏晚」\n\n"
            "【参考】@Image1＝CHAR_01；@Image2＝CHAR_02\n"
            "【公共总规范】全段1拍0次硬切。阿泽（@Image1）：黑色碎短发。\n"
            "【时间轴】\n0-30秒，镜头：中景。\n"
            "【收尾】出口状态：无。\n"
        )
        errors, warnings = [], []
        validator.check_prompt(
            prompt, "E01", "SH01", 30, {"角色": ["CHAR_01", "CHAR_02"]},
            POLICY, errors, char_names={"CHAR_01": "阿泽", "CHAR_02": "苏晚"},
            model="wan30", warnings=warnings,
            asset_codes={"CHAR_01", "CHAR_02"}, asset_prompts={})
        self.assertFalse(any("WAN30-03" in e for e in errors), errors)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
