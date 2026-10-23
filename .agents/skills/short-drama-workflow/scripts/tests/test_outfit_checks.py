#!/usr/bin/env python3
"""服装变体检查的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_outfit_checks.py
覆盖 validate_compact_package.py 的 check_outfit_consistency：归属缺失、
参考未写归属、与固定服装冲突、同片段多套、场合级服装词无资产。
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

LOCK = "声线锁定：CHAR_01 陈川＝26岁男声，中低音清冷略沙。"

HEAD = """# 精简制作包

## 固定资产

### 角色 CHAR_01｜陈川

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。固定服装：墨绿飞行员夹克，哑光尼龙面料，袖口螺纹起球；白色圆领内搭。
```

### 角色 CHAR_02｜林悦

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。固定服装：米白色细针织衫，领口平整，袖口微松。
```

### 场景 LOC_01｜婚礼院子

#### 图片提示词

```text
真实现场照片，35mm 胶片质感，低饱和，不锐化。生成16:9横版单张全景基准图。画面中无人物。本卡是场景底板：只锁空间、光位与材质；车辆、人物与道具由片段绑定与站位承载。
```
"""

OUTFIT_ASSET = """
### 道具 PROP_09｜陈川·婚礼西装

#### 图片提示词

```text
真实服装产品摄影，真实面料纹理与缝线，物理光照，自然褶皱与垂坠；不做 3D 渲染，不做塑料感，不磨皮。
16:9 单张平铺服装图：浅灰无缝背景，俯拍平铺，一套衣服的各件分区摆放、互不遮挡；画面里没有人体、没有人脸、没有模特、没有手，不是多格拼版、不是设定板、不是穿着图。
套装清单：深藏青单排扣羊毛西装外套，垫肩略方，哑光牛角扣两粒；白色府绸衬衫；炭灰西裤，裤线笔挺；黑色系带皮鞋。
本套装供 CHAR_01 穿着，沿用 CHAR_01 身份母版的脸、发型与身形比例；与默认装为同一人物的另一套穿着，不是新人物。
负向限制：3D 渲染、CG、卡通、人体、人脸、模特、多格拼版、可读文字、水印。
```
"""

EPISODE = """
## 剧集 E01｜婚礼当天

### 小说原文

```text
第一集的小说原文。
```

### 片段 SH01｜30秒｜{title}

角色：{chars}
场景：LOC_01
{props}
#### 视频提示词

```text
【参考】{ref}
【公共总规范】统一现实主义电影质感。{lock}
【时间轴】
{rows}
【收尾】画面定住。
```
"""

ROWS_CASUAL = "\n".join([
    '0-5秒，他站在院子里，镜头平视不动。',
    '5-10秒，硬切，风吹过树梢。',
    '10-15秒，硬切，远处有车灯。',
    '15-20秒，硬切，他停住脚步。',
    '20-25秒，硬切，身后传来人声。',
    '25-30秒，硬切，他呼出一口气。',
])


def build(*, with_outfit_asset: bool = False, rows: str = ROWS_CASUAL,
          chars: str = "CHAR_01", props: str = "", ref: str = "CHAR_01=陈川外观锁定；LOC_01=婚礼院子。",
          title: str = "婚礼当天", lock: str = LOCK) -> str:
    head = HEAD + (OUTFIT_ASSET if with_outfit_asset else "")
    return head + EPISODE.format(title=title, chars=chars, props=props, ref=ref,
                                 lock=lock, rows=rows)


def run(package: str) -> tuple[list, list]:
    result = validator.validate(package, POLICY)
    return result["errors"], result["warnings"]


class OutfitCheckTest(unittest.TestCase):
    def test_casual_outfit_passes(self):
        errors, warnings = run(build())
        self.assertEqual([e for e in errors if "服装" in e or "上装" in e], [])
        self.assertEqual([w for w in warnings if "服装" in w], [])

    def test_outfit_asset_owner_not_bound_is_error(self):
        package = build(with_outfit_asset=True, chars="CHAR_02",
                        props="道具：PROP_09\n",
                        ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。")
        errors, _ = run(package)
        self.assertTrue(any("声明供 CHAR_01 穿着" in e for e in errors), errors)

    def test_outfit_asset_owner_not_written_in_reference_is_error(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=一套西装；LOC_01=婚礼院子。")
        errors, _ = run(package)
        self.assertTrue(any("没有写明由谁穿着" in e for e in errors), errors)

    def test_wedding_word_without_outfit_asset_is_warning(self):
        rows = ROWS_CASUAL.replace(
            "他站在院子里", "他穿着那套藏青西装站在院子里")
        _, warnings = run(build(rows=rows))
        self.assertTrue(any("场合级服装词" in w for w in warnings), warnings)

    def test_conflict_with_locked_outfit_is_error(self):
        rows = ROWS_CASUAL.replace(
            "他站在院子里", "他穿着那套西装站在院子里")
        errors, _ = run(build(rows=rows))
        self.assertTrue(any("锁定" in e and "西装" in e for e in errors), errors)

    def test_two_outfits_without_change_action_is_error(self):
        rows = (ROWS_CASUAL.replace("他站在院子里", "他穿着西装站在院子里")
                .replace("他停住脚步", "他这身夹克还是旧的，停住脚步"))
        errors, _ = run(build(rows=rows))
        self.assertTrue(any("多套上装" in e for e in errors), errors)

    def test_costume_change_with_visible_action_is_warning(self):
        rows = (ROWS_CASUAL.replace("他站在院子里", "他穿着西装站在院子里")
                .replace("他停住脚步", "他脱下西装换上夹克，停住脚步"))
        errors, warnings = run(build(rows=rows))
        self.assertTrue(any("换了装" in w for w in warnings), warnings)
        self.assertEqual([e for e in errors if "多套上装" in e], [])

    def test_other_characters_coat_not_counted(self):
        rows = ("0-5秒，林悦穿着白色连衣裙站在他旁边，他站在院子里，镜头平视不动。\n"
                + "\n".join(ROWS_CASUAL.split("\n")[1:]))
        errors, _ = run(build(rows=rows, chars="CHAR_01,CHAR_02"))
        self.assertEqual([e for e in errors if "多套上装" in e], [])

    def test_outfit_asset_bound_and_named_passes(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。")
        errors, _ = run(package)
        self.assertEqual([e for e in errors if "服装" in e], [])

    def test_costume_worn_by_named_character_is_detected(self):
        rows = ROWS_CASUAL.replace("他站在院子里", "陈川穿着西装站在院子里")
        errors, _ = run(build(rows=rows))
        self.assertTrue(any("锁定" in e for e in errors), errors)

    def test_outfit_worn_person_is_error(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。")
        package = package.replace(
            "16:9 单张平铺服装图：浅灰无缝背景，俯拍平铺，一套衣服的各件分区摆放、互不遮挡",
            "16:9 单张单人穿着全身图：陈川站在中性浅灰无缝背景前")
        errors, _ = run(package)
        self.assertTrue(any("人体/人脸/模特" in e for e in errors), errors)

    # ---- 2026-10-23 实证：服装变体生成成 3D 卡通 + 与默认装两套真值 ----
    def test_outfit_board_layout_is_error(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。")
        package = package.replace("16:9 单张平铺服装图",
                                  "16:9 服饰设定板，平铺与穿着态并列")
        errors, _ = run(package)
        self.assertTrue(any("单张单主体" in e for e in errors), errors)

    def test_outfit_missing_style_anchor_is_error(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。")
        package = package.replace(
            "真实服装产品摄影，真实面料纹理与缝线，物理光照，自然褶皱与垂坠；"
            "不做 3D 渲染，不做塑料感，不磨皮。", "")
        errors, _ = run(package)
        self.assertTrue(any("缺风格锚" in e for e in errors), errors)

    def test_outfit_reference_without_unique_is_error(self):
        package = build(with_outfit_asset=True, props="道具：PROP_09\n",
                        ref="PROP_09=陈川婚礼西装，CHAR_01 穿着；LOC_01=婚礼院子。")
        errors, _ = run(package)
        self.assertTrue(any("唯一基准" in e for e in errors), errors)

    def test_variant_bound_but_anchor_keeps_default_is_error(self):
        package = build(
            with_outfit_asset=True, props="道具：PROP_09\n",
            ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。",
            lock="【角色一致性】陈川：黑色短发／细金属框眼镜／墨绿飞行员夹克。")
        errors, _ = run(package)
        self.assertTrue(any("仍写默认装" in e for e in errors), errors)

    def test_variant_bound_and_anchor_switched_passes(self):
        package = build(
            with_outfit_asset=True, props="道具：PROP_09\n",
            ref="PROP_09=本段服装唯一基准，由 CHAR_01 穿着；LOC_01=婚礼院子。",
            lock="【角色一致性】陈川：黑色短发／细金属框眼镜／深藏青羊毛西装外套。")
        errors, _ = run(package)
        self.assertEqual([e for e in errors if "服装" in e or "默认装" in e], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
