#!/usr/bin/env python3
"""validate_workflow_manifest.py 的回归自测。

运行：python3 scripts/tests/test_workflow_manifest.py

覆盖：
  · 生成轨与 06 机检命令一致才通过；
  · 阶段 1 评审缺失在 strict 下判错、基础模式下只提醒；
  · 05a/05b 分拆必须有 05-评审索引.md；
  · 多个非备份包判错。
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "workflow_manifest", ROOT / "scripts" / "validate_workflow_manifest.py"
)
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class WorkflowManifestTest(unittest.TestCase):
    def make_project(self, tmp: str, *, branch: str = "wan30", with_01c: bool = True,
                     split_review: bool = False, with_index: bool = True,
                     gate_model: str | None = None) -> Path:
        workdir = Path(tmp) / "作品"
        internal = workdir / "内部"
        internal.mkdir(parents=True)
        (internal / "00-项目输入单.md").write_text(
            f"# 输入单\n\n| 项 | 值 |\n|---|---|\n| 生成模型 | "
            f"{'Wan3.0（--model wan30 轨）' if branch == 'wan30' else 'MiniMax H3（--model h3 轨）' if branch == 'h3' else 'Seedance 2.5（--model seedance25 轨）'} |\n",
            encoding="utf-8",
        )
        (workdir / "精简制作包-测试.md").write_text("# 包\n", encoding="utf-8")
        (internal / "06-机检结果.txt").write_text(
            "python3 validate_compact_package.py 包 --model "
            + (gate_model or branch)
            + "\n结果：0 错误\n",
            encoding="utf-8",
        )
        (internal / "执行账.md").write_text(
            f"# 执行账\n\n生成轨：{branch}\n\n| 阶段 | 结论 | 证据 |\n|---|---|---|\n| 0 | 通过 | 输入单 |\n",
            encoding="utf-8",
        )
        if with_01c:
            (internal / "01c-剧情评审.md").write_text(
                "# 剧情评审\n\n## 评审 1（事件/分集）\n结论：通过。证据：事件表与分集规划逐项核对，"
                "主线因果、人物目标与集末钩子均有原文依据，未发现无证据改动。\n\n"
                "## 评审 2（逐集剧本）\n结论：通过。证据：逐集剧本的台词、动作与场景可拍性已核对，"
                "关键反转和人物知情顺序未变。\n\n"
                "## 评审 3（片段规划）\n结论：通过。证据：片段入口、出口与跨段承接已逐条比对，"
                "未发现为凑切镜新增的无信息镜头；三次评审均由独立子任务完成并记录证据。\n",
                encoding="utf-8",
            )
        if split_review:
            (internal / "05a-复评-剧情连续性.md").write_text("评审结论：通过\n", encoding="utf-8")
            (internal / "05b-复评-画面表演.md").write_text("评审结论：通过\n", encoding="utf-8")
            if with_index:
                (internal / "05-评审索引.md").write_text(
                    "# 评审索引\n\n05a：剧情连续性\n05b：画面表演\n结论：通过\n", encoding="utf-8"
                )
        else:
            (internal / "05-提示词评审与整改.md").write_text(
                "# 提示词评审\n\n评审结论：通过\n评稿人：子任务 R-09\n", encoding="utf-8"
            )
        return workdir

    def test_valid_wan_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = manifest.validate(self.make_project(tmp), strict=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["branch"], "wan30")

    def test_missing_stage1_is_strict_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self.make_project(tmp, with_01c=False)
            strict = manifest.validate(workdir, strict=True)
            basic = manifest.validate(workdir, strict=False)
        self.assertFalse(strict["ok"])
        self.assertTrue(any("01c" in e for e in strict["errors"]))
        self.assertTrue(basic["ok"], basic)

    def test_gate_model_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = manifest.validate(self.make_project(tmp, gate_model="h3"), strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("不一致" in e for e in result["errors"]))

    def test_split_review_requires_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = manifest.validate(
                self.make_project(tmp, split_review=True, with_index=False), strict=True
            )
        self.assertFalse(result["ok"])
        self.assertTrue(any("05-评审索引" in e for e in result["errors"]))

    def test_multiple_packages_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self.make_project(tmp)
            (workdir / "精简制作包-另一个.md").write_text("# 另一个\n", encoding="utf-8")
            result = manifest.validate(workdir, strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("多个非备份" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
