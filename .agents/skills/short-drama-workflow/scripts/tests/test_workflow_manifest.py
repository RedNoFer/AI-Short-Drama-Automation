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


def package_text(prompts=("提示词正文",), fence="```"):
    text = "# 精简制作包\n\n## 固定资产\n\n## 剧集 E01｜开场\n\n"
    text += f"### 小说原文\n{fence}text\n原文中包含标题示例：\n## 剧集 E99｜原文引文\n{fence}\n\n"
    for i, prompt in enumerate(prompts, 1):
        text += (f"### 片段 SH{i:02d}｜30秒｜片段{i}\n\n#### 视频提示词\n"
                 f"{fence}text\n{prompt}\n{fence}\n\n")
    return text


def review_text(hashes):
    rows = "\n".join(f"| {sid} | {digest} | 通过 |" for sid, digest in hashes.items())
    return ("# 提示词评审\n评稿人：独立子任务 R-09\n"
            "| 片段 | 正文 SHA-256 | 结论 |\n|---|---|---|\n" + rows
            + "\n结论：通过\n未关闭阻断/重要缺陷：0\n")


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
        package = workdir / "精简制作包-测试.md"
        package.write_text(package_text(), encoding="utf-8")
        hashes, issues = manifest._package_prompt_hashes(package)
        self.assertEqual(issues, [])
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
            (internal / "05a-复评-剧情连续性.md").write_text(review_text(hashes), encoding="utf-8")
            (internal / "05b-复评-画面表演.md").write_text(review_text({}), encoding="utf-8")
            if with_index:
                (internal / "05-评审索引.md").write_text(
                    "# 评审索引\n\n05a：剧情连续性\n05b：画面表演\n结论：通过\n未关闭阻断/重要缺陷：0\n", encoding="utf-8"
                )
        else:
            (internal / "05-提示词评审与整改.md").write_text(
                review_text(hashes), encoding="utf-8"
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

    def test_nested_evidence_does_not_hide_parent_verdict(self):
        text = "## 事件/分集\n### 证据\n因果与原文一致。\n结论：通过\n## 逐集剧本\n结论：需修改\n"
        self.assertTrue(manifest._section_pass(text, "事件/分集"))
        self.assertFalse(manifest._section_pass(text, "逐集剧本"))
        self.assertFalse(manifest._section_pass(
            "## 事件/分集\n### 证据\n待核。\n## 逐集剧本\n结论：通过\n", "事件/分集"))

    def test_changed_prompt_invalidates_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp)
            (work / "精简制作包-测试.md").write_text(package_text(("提示词已修改",)), encoding="utf-8")
            result = manifest.validate(work, strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("正文 SHA-256" in item for item in result["errors"]))

    def test_global_summary_still_blocks_stage_with_passing_segment_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp)
            report = work / "内部" / "05-提示词评审与整改.md"
            report.write_text(report.read_text(encoding="utf-8").replace(
                "结论：通过", "结论：需修改").replace(
                "未关闭阻断/重要缺陷：0", "未关闭阻断/重要缺陷：1"), encoding="utf-8")
            result = manifest.validate(work, strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("未关闭阻断/重要缺陷" in item for item in result["errors"]))

    def test_old_local_pass_cannot_override_failing_global_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp)
            report = work / "内部" / "05-提示词评审与整改.md"
            report.write_text(report.read_text(encoding="utf-8")
                             + "\n## 全局汇总\n结论：需修改\n未关闭阻断/重要缺陷：1\n", encoding="utf-8")
            result = manifest.validate(work, strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("全局汇总" in item for item in result["errors"]))

    def test_added_segment_requires_review_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp)
            (work / "精简制作包-测试.md").write_text(package_text(("提示词正文", "新增提示词")), encoding="utf-8")
            result = manifest.validate(work, strict=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("未覆盖片段 E01-SH02" in item for item in result["errors"]))

    def test_hashes_follow_import_parser_and_preserve_prompt_whitespace(self):
        prompt = "\n  保留正文空格\n下一行\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "包.md"
            for fence in ("```", "~~~"):
                path.write_text(package_text((prompt,), fence), encoding="utf-8")
                hashes, errors = manifest._package_prompt_hashes(path)
                self.assertEqual(errors, [])
                self.assertEqual(hashes, {"E01-SH01": manifest.wc.sha256_text(prompt)})

    def test_parallel_review_index_accepts_three_shards_and_checks_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp)
            internal = work / "内部"
            (internal / "05-提示词评审与整改.md").unlink()
            package = work / "精简制作包-测试.md"
            package.write_text(package_text(("第一段", "第二段", "第三段")), encoding="utf-8")
            hashes, _ = manifest._package_prompt_hashes(package)
            files = []
            for suffix, (sid, digest) in zip("abc", hashes.items()):
                report = internal / f"05{suffix}-独立评审.md"
                report.write_text(review_text({sid: digest}), encoding="utf-8")
                files.append(report)
            (internal / "05-评审索引.md").write_text(
                "\n".join(p.name for p in files) + "\n结论：通过\n未关闭阻断/重要缺陷：0\n", encoding="utf-8")
            (internal / "05z-未采用草案.md").write_text("结论：需修改\n", encoding="utf-8")
            self.assertTrue(manifest.validate(work, strict=True)["ok"])
            files[-1].write_text(review_text({"E01-SH03": hashes["E01-SH03"]}).replace(
                "结论：通过", "结论：需修改"), encoding="utf-8")
            result = manifest.validate(work, strict=True)
            self.assertFalse(result["ok"])
            self.assertTrue(any("05c-独立评审.md" in item for item in result["errors"]))

    def test_each_coverage_row_requires_explicit_pass(self):
        expected = {"E01-SH01": "a" * 64}
        for verdict in ("需修改", "待评", "", "通过，仍有重要缺陷"):
            with self.subTest(verdict=verdict):
                report = f"| E01-SH01 | {'a' * 64} | {verdict} |\n结论：通过\n"
                self.assertTrue(manifest._review_hash_coverage(report, expected))
        self.assertEqual(manifest._review_hash_coverage(review_text(expected), expected), [])

    def test_duplicate_or_conflicting_coverage_rows_fail(self):
        expected = {"E01-SH01": "a" * 64}
        first = f"| E01-SH01 | {'a' * 64} | 通过 |\n"
        for second in (first, f"| E01-SH01 | {'a' * 64} | 需修改 |\n",
                       f"| E01-SH01 | {'b' * 64} | 通过 |\n"):
            with self.subTest(second=second):
                self.assertTrue(manifest._review_hash_coverage(first + second, expected))

    def test_coverage_ignores_fenced_examples(self):
        expected = {"E01-SH01": "a" * 64}
        row = f"| E01-SH01 | {'a' * 64} | 通过 |\n"
        for fence in ("```", "~~~"):
            with self.subTest(fence=fence):
                example = f"{fence}md\n{row}{fence}\n"
                self.assertTrue(manifest._review_hash_coverage(example, expected))
                self.assertEqual(manifest._review_hash_coverage(example + row, expected), [])

    def test_split_index_summary_does_not_count_as_review_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.make_project(tmp, split_review=True)
            internal = work / "内部"
            hashes, _ = manifest._package_prompt_hashes(work / "精简制作包-测试.md")
            index = internal / "05-评审索引.md"
            index.write_text(index.read_text(encoding="utf-8") + review_text(hashes), encoding="utf-8")
            self.assertTrue(manifest.validate(work, strict=True)["ok"])
            (internal / "05a-复评-剧情连续性.md").write_text(review_text({}), encoding="utf-8")
            result = manifest.validate(work, strict=True)
            self.assertFalse(result["ok"])
            self.assertTrue(any("未覆盖片段 E01-SH01" in e for e in result["errors"]), result)


if __name__ == "__main__":
    unittest.main()
