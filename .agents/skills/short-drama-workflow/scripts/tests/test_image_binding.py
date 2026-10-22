#!/usr/bin/env python3
"""图片编号规则的回归自测：按轨区分 + Wan3.0 轨的编号与指向一致性。

运行：python3 scripts/tests/test_image_binding.py
覆盖：Seedance/H3 轨不得预写 @Image/@图片 编号；Wan3.0 轨允许 @Image 多模态
参考，但编号须从 1 连续、指向的资产必须在固定资产区有定义。
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

### 角色 CHAR_02｜小林

#### 图片提示词

```text
生成16:9横版白底角色四视图设定图。
```

### 场景 LOC_01｜起点

#### 图片提示词

```text
生成16:9横版单张全景基准图。
```

### 道具 PROP_01｜包裹

#### 图片提示词

```text
生成16:9横版单主体道具基准图。
```

## 剧集 E01｜测试集

### 小说原文

```text
第一集的小说原文。
```

### 片段 SH01｜30秒｜测试片段

角色：CHAR_01
场景：LOC_01
道具：PROP_01

#### 视频提示词

```text
【参考】{ref}
【公共总规范】统一3D国漫画风。{lock}
【时间轴】
{rows}
【收尾】他走远。
```
"""

ROWS = "\n".join([
    '0-5秒，他站在雨里，镜头平视不动，他作口型对白、口型同步，说："你好。"',
    '5-10秒，硬切，风吹过路面，他侧头听声。',
    '10-15秒，硬切，远处雾里有光，他向前一步。',
    '15-20秒，硬切，他停住脚步，眉头收紧。',
    '20-25秒，硬切，身后车灯扫过，雨幕发亮。',
    '25-30秒，硬切，他呼出白气，画面定住。',
])


def build(ref: str) -> str:
    return PACKAGE.format(ref=ref, lock=LOCK, rows=ROWS)


def run(ref: str, model: str = "seedance25") -> tuple[list, list]:
    result = validator.validate(build(ref), POLICY, model=model)
    return result["errors"], result["warnings"]


class ImageBindingTest(unittest.TestCase):
    def test_seedance_rejects_compact_image_number(self):
        errors, _ = run("CHAR_01=阿泽外观锁定；LOC_01=起点路段。@Image1＝CHAR_01 阿泽。")
        self.assertTrue(any("不得预写 @Image" in e for e in errors), errors)

    def test_seedance_rejects_image_number_without_space(self):
        errors, _ = run("@Image1＝CHAR_01 阿泽外观锁定；LOC_01=起点路段。")
        self.assertTrue(any("不得预写 @Image" in e for e in errors), errors)

    def test_seedance_rejects_chinese_image_number(self):
        errors, _ = run("@图片1＝CHAR_01 阿泽外观锁定；LOC_01=起点路段。")
        self.assertTrue(any("不得预写 @Image" in e for e in errors), errors)

    def test_seedance_rejects_chinese_image_number_with_space(self):
        errors, _ = run("@图片 1＝CHAR_01 阿泽外观锁定；LOC_01=起点路段。")
        self.assertTrue(any("不得预写 @Image" in e for e in errors), errors)

    def test_seedance_clean_package_passes(self):
        errors, _ = run("CHAR_01=阿泽外观锁定；LOC_01=起点路段；PROP_01=牛皮纸包裹。")
        self.assertEqual([e for e in errors if "@Image" in e or "@图片" in e], [])

    def test_wan30_allows_image_number(self):
        errors, _ = run("CHAR_01=阿泽外观锁定；LOC_01=起点路段。@Image1＝CHAR_01 阿泽。",
                        model="wan30")
        self.assertEqual([e for e in errors if "不得预写" in e], [])

    def test_wan30_requires_contiguous_numbering(self):
        errors, _ = run("@Image1＝CHAR_01 阿泽；@Image3＝LOC_01 起点路段。", model="wan30")
        self.assertTrue(any("连续编号" in e for e in errors), errors)

    def test_wan30_rejects_undefined_asset(self):
        errors, _ = run("@Image1＝CHAR_01 阿泽；@Image2＝CHAR_99 不存在。", model="wan30")
        self.assertTrue(any("没有定义" in e for e in errors), errors)

    def test_wan30_warns_on_unbound_asset(self):
        errors, warnings = run("@Image1＝CHAR_01 阿泽；@Image2＝CHAR_02 小林。",
                               model="wan30")
        self.assertEqual([e for e in errors if "未绑定" in e], [])
        self.assertTrue(any("未绑定到本片段" in w for w in warnings), warnings)

    def test_h3_rejects_image_number(self):
        errors, _ = run("@Image1＝CHAR_01 阿泽外观锁定；LOC_01=起点路段。", model="h3")
        self.assertTrue(any("不得预写 @Image" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
