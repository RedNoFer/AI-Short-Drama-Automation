"""Version and evidence regressions; fixtures are not real work reviews."""
import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

FAST = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_record", FAST / "review_record.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
SCRIPTS = FAST.parents[1] / "short-drama-workflow" / "scripts"


class ReviewRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "内部").mkdir()
        self.package = self.root / "精简制作包.md"
        self.package.write_text('# 精简制作包\n\n## 剧集 E01｜测试\n### 片段 SH01｜30秒｜测试\n角色：CHAR_01\n#### 视频提示词\n\n```text\n【参考】CHAR_01＝身份基准。\n【时间轴】\n0-30秒，阿泽打开箱盖取出血袋。\n【收尾】血袋在手。\n```\n')
        source = self.root / "源文.md"
        source.write_text("阿泽打开箱盖，拿出了血袋。")
        self.record = self.root / "内部" / "验收记录.json"
        self.data = dict(package_sha256=review.digest(self.package),
            review_mode="author_self_check", reviewer="fixture",
            media_status=dict(references="pending", submission="pending", video="pending"),
            inputs=[dict(file="源文.md", sha256=review.digest(source))],
            segments=[dict(episode="E01", shot="SH01", status="pass",
                prompt_quote="阿泽打开箱盖取出血袋", source_file="源文.md",
                source_quote="阿泽打开箱盖，拿出了血袋。", event_mapping="开箱取袋→首镜",
                quality={f: "夹具中的具体判断" for f in review.QUALITY_FIELDS},
                state_interfaces="合盖→开箱取袋→血袋在手", defects=[])])

    def check(self):
        self.record.write_text(json.dumps(self.data, ensure_ascii=False))
        return review.check_review(self.package, SCRIPTS)

    def test_current_complete_record_passes(self):
        self.assertEqual(self.check(), [])

    def test_missing_record_blocks(self):
        self.assertTrue(review.check_review(self.package, SCRIPTS))

    def test_edited_package_invalidates_review(self):
        self.package.write_text(self.package.read_text() + "修订")
        self.assertTrue(any("SHA-256" in e for e in self.check()))

    def test_edited_source_invalidates_review(self):
        (self.root / "源文.md").write_text("阿泽看着箱子。")
        self.assertTrue(any("依据文件已变更" in e for e in self.check()))

    def test_missing_or_duplicate_fragment_blocks(self):
        self.data["segments"] = []
        self.assertTrue(self.check())
        self.setUp()
        self.data["segments"] *= 2
        self.assertTrue(any("重复" in e for e in self.check()))

    def test_fabricated_quote_and_open_defect_block(self):
        self.data["segments"][0].update(prompt_quote="不存在的原文", defects=[dict(status="open")])
        errors = self.check()
        self.assertTrue(any("引文不存在" in e for e in errors))
        self.assertTrue(any("缺陷未关闭" in e for e in errors))

    def test_missing_quality_dimension_blocks(self):
        del self.data["segments"][0]["quality"]["capacity"]
        self.assertTrue(any("六项" in e for e in self.check()))

    def test_self_review_cannot_be_labelled_independent(self):
        self.data.update(review_mode="independent_review", author="fixture")
        self.assertTrue(any("不同的作者" in e for e in self.check()))

    def test_delivery_cli_blocks_missing_record(self):
        sys.path.insert(0, str(FAST))
        import fast_gate
        def fake_run(cmd):
            return (0, '{"issues": []}' if "--json" in cmd else "机械通过", "")
        output = io.StringIO()
        with patch.object(sys, "argv", ["fast_gate", str(self.package), "--novel", str(self.root / "源文.md"), "--delivery", "--json"]), patch.object(fast_gate, "_run", side_effect=fake_run), contextlib.redirect_stdout(output):
            self.assertEqual(fast_gate.main(), 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["scope"], "delivery_record_and_mechanical")
        self.assertTrue(any(block["step"] == "4 最终验收版本" for block in report["hard_errors"]))

    def test_delivery_cli_does_not_skip_source_coverage(self):
        sys.path.insert(0, str(FAST))
        import fast_gate
        self.check()
        output = io.StringIO()
        def fake_run(cmd):
            return (0, '{"issues": []}' if "--json" in cmd else "机械通过", "")
        with patch.object(sys, "argv", ["fast_gate", str(self.package), "--delivery", "--json"]), patch.object(fast_gate, "_run", side_effect=fake_run), contextlib.redirect_stdout(output):
            self.assertEqual(fast_gate.main(), 1)
        self.assertTrue(any(block["step"] == "交付依据" for block in json.loads(output.getvalue())["hard_errors"]))


if __name__ == "__main__":
    unittest.main()
