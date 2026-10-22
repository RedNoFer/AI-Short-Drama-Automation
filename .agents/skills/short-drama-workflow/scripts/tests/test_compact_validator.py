#!/usr/bin/env python3
"""validate_compact_package.py 的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_compact_validator.py
新增/修改校验规则时先跑本测试；PROC-02 记录过校验器自身回归。
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compact_validator", ROOT / "scripts" / "validate_compact_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
POLICY = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))

HEADER = """# 精简制作包

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
【公共总规范】统一3D国漫画风。{pad}{lock}
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

LOCK = "声线锁定：CHAR_01 阿泽＝26岁男声，中低音清冷略沙。"


def make_package(*, lock: str = LOCK, rows: str | None = None,
                 include_param: bool = False, second_episode: bool = False,
                 second_lock: str | None = None, title_suffix: str = "",
                 dur: int = 30, pad: str = "") -> str:
    rows = (rows or GOOD_ROWS).format(ep="E01", sh="SH01")
    first = EPISODE_TMPL.format(ep="E01", sh="SH01", n=1, lock=lock, rows=rows,
                                suffix=title_suffix, dur=dur, pad=pad)
    if include_param:
        first = first.replace("【参考】", "【参数】剧集E01片段SH01；30秒。\n【参考】", 1)
    body = HEADER + first
    if second_episode:
        rows2 = GOOD_ROWS.format(ep="E02", sh="SH01")
        body += EPISODE_TMPL.format(ep="E02", sh="SH01", n=2, lock=second_lock or lock, rows=rows2, suffix="", dur=dur, pad=pad)
    return body


ONER_ROWS = "\n".join([
    '0-4秒，狼群自雾中压低身躯围拢，镜头贴地跟移，阿泽横刀立定，刀刃映出绿光。',
    '4-14秒，镜头不停，随他侧身滑步绕行，狼影扑至时他拧腰格挡、刀背磕开兽爪，借冲力翻身换位，焦点在兽瞳与刀刃之间快速切换，雾气被劲风撕开一道口子。',
    '14-24秒，镜头随他蹬地跃起升至高位俯瞰，狼群合围成环，他落回圈内以攻代守，刀光连成弧面，每一记挥砍都逼得最近的狼影后撤半步。',
    '24-30秒，镜头缓缓拉远升高，一人一环狼对峙于雾心，他收刀入鞘，绿光在雾里明灭。',
])

WAN_ROWS = "\n".join([
    '0-1.5秒，阿泽立在零公里路牌下，晨雾漫过路面，镜头贴地缓升。',
    '1.5-4秒，硬切，牛皮纸包裹特写，绳结与纸纹清晰可辨。',
    '4-9秒，硬切，他拆开包装，泛黄古图徐徐展开，镜头缓推。',
    '9-14.5秒，硬切，字条特写，他瞳孔微收，指节泛白。',
    '14.5-22秒，硬切，五人围拢，焦点在字迹与面孔之间缓慢转换。本镜画面内恰好五人：左起阿泽、苏晚、老杨、许棠、小林；每人只有一个身体、一张脸；不出现第六人。',
    '22-30秒，硬切，古图边缘银纹微亮，他收图入怀，雾从车头漫过。',
])

WAN_PAD = "一致性枚举：阿泽碎短发垂额、深灰冲锋衣、左手腕旧手绳全程佩戴；" * 230


class CompactValidatorTests(unittest.TestCase):
    def test_good_package_passes(self):
        result = validator.validate(make_package(), POLICY)
        self.assertTrue(result["ok"], result["errors"])

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
        drifted = "声线锁定：CHAR_01 阿泽＝高亢尖细的少年音。"
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
        result = validator.validate(make_package(rows=ONER_ROWS, title_suffix="·一镜到底"), POLICY)
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
        pkg = make_package(rows=WAN_ROWS, pad=WAN_PAD)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["stats"][0]["model"], "wan30")
        # 同一包在 Seedance 轨下必须失败（小数行 + 超 3000 字符）
        bad = validator.validate(pkg, POLICY, space_exempt=True)
        self.assertFalse(bad["ok"])

    def test_group_shot_requires_headcount_lock(self):
        """四人以上同框必须写人数锁定句（WAN30-02 第 3 条）。"""
        rows = WAN_ROWS.replace(
            "本镜画面内恰好五人：左起阿泽、苏晚、老杨、许棠、小林；"
            "每人只有一个身体、一张脸；不出现第六人。", "")
        pkg = make_package(rows=rows, pad=WAN_PAD)
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
        pkg = make_package(rows=rows, pad=WAN_PAD)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_first_beat_must_not_write_hard_cut(self):
        """首拍不得写「硬切」——首镜直写开场，硬切只用于其后每一拍。"""
        rows = WAN_ROWS.replace("0-1.5秒，阿泽立在", "0-1.5秒，硬切，阿泽立在", 1)
        pkg = make_package(rows=rows, pad=WAN_PAD)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("首拍不得写" in e for e in result["errors"]), result["errors"])

    def test_public_shot_count_declaration_must_match(self):
        """公共总规范自报的「全段 N 拍 M 次硬切」须与正文一致。"""
        pkg = make_package(rows=WAN_ROWS, pad=WAN_PAD)
        pkg = pkg.replace("【公共总规范】", "【公共总规范】全段 9 拍 8 次硬切；", 1)
        result = validator.validate(pkg, POLICY, model="wan30", space_exempt=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("与正文不符" in e for e in result["errors"]), result["errors"])

    def test_wan30_duration_bounds(self):
        rows24 = WAN_ROWS.replace("14.5-22秒", "14.5-20秒").replace("22-30秒", "20-24秒")
        pkg = make_package(rows=rows24, pad=WAN_PAD, dur=24)
        self.assertTrue(validator.validate(pkg, POLICY, model="wan30", space_exempt=True)["ok"])
        self.assertFalse(validator.validate(pkg, POLICY, space_exempt=True)["ok"])

    def test_wan30_granularity_rejected(self):
        bad_rows = WAN_ROWS.replace("1.5-4秒", "1.7-4秒", 1)
        result = validator.validate(make_package(rows=bad_rows, pad=WAN_PAD), POLICY, model="wan30")
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
            "生成16:9横版白底角色四视图设定图。",
            "生成16:9横版单张电影剧照，单人入画，3/4 侧身。")
        result = validator.validate(pkg, POLICY)
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
