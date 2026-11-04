"""fast_gate.py 合同测试：不依赖有效包，验证硬错路径与输出契约。"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

FAST_DIR = Path(__file__).resolve().parents[2]
FAST_GATE = FAST_DIR / "scripts" / "fast_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("fast_gate", FAST_GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ExistenceTest(unittest.TestCase):
    def test_wrapped_validators_exist(self):
        scripts = FAST_DIR.parent / "short-drama-workflow" / "scripts"
        for name in (
            "validate_compact_package.py",
            "audit_wan30_antipatterns.py",
            "validate_novel_coverage.py",
        ):
            self.assertTrue((scripts / name).exists(), f"缺少被封装脚本：{name}")


class GateCliTest(unittest.TestCase):
    def test_missing_package_returns_2(self):
        mod = _load_module()
        rc, out, err = mod._run(
            [sys.executable, str(FAST_GATE), "/nonexistent/pkg.md"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("找不到文件", err)

    def test_fixture_makes_coherent_report(self):
        """坏夹具应产出硬错报告且退出码非 0，不崩溃不挂起。"""
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "pkg.md"
            pkg.write_text(
                "# 精简制作包\n\n## 剧集 E01｜测试\n\n```text\n gibberish \n```\n",
                encoding="utf-8",
            )
            rc, out, err = mod._run(
                [sys.executable, str(FAST_GATE), str(pkg), "--json"]
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("hard_errors", out)

    def test_r39_missing_line_detected(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "pkg.md"
            pkg.write_text(
                "#### 视频提示词\n\n```text\n"
                "【公共总规范】\n声音纪律：无BGM。\n"
                "0-3秒，镜头：中景，35mm，平视。画面：他作口型对白、口型同步说“你好”。声音：脚步。\n"
                "```\n",
                encoding="utf-8",
            )
            issues = mod._r39_check(pkg)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["kind"], "missing_text_discipline_line")

    def test_r39_discipline_line_passes(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "pkg.md"
            pkg.write_text(
                "#### 视频提示词\n\n```text\n"
                "【公共总规范】\n画面文字纪律：全片每一帧（含首帧和尾帧）画面内不存在任何文字层。\n"
                "0-3秒，镜头：中景，35mm。画面：他作口型对白、口型同步说“你好”。\n"
                "```\n",
                encoding="utf-8",
            )
            self.assertEqual(mod._r39_check(pkg), [])

    def test_non_speech_block_needs_no_line(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "pkg.md"
            pkg.write_text(
                "#### 视频提示词\n\n```text\n"
                "0-3秒，镜头：全景，35mm。画面：空街空镜，雾气飘动。\n"
                "```\n",
                encoding="utf-8",
            )
            self.assertEqual(mod._r39_check(pkg), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
