#!/usr/bin/env python3
"""统一测试入口：一条命令跑完 skill 的全部脚本自测（改造五配套）。

为什么有这个文件（2026-10-25 流程优化）
--------------------------------------------------------------------------
此前 18 个测试文件靠人逐个手点，结果「改造把 22 条测试打红」整整一天没人发现——
不是没人跑，是没人**全跑**。本入口把全跑变成默认动作：

    python3 scripts/tests/run_all.py

退出码 0 才算通过，可直接接进交付前的自检。

LEGACY：两份历史样本测试不再纳入
--------------------------------------------------------------------------
`test_outfit_checks.py` 与 `test_space_sync.py` 的 fixture 是旧版通用四视图包，
早于「生成轨唯一登记＋失败关闭」这条规则，且与当前 Wan3.0 版式/字符口径不同源。
它们的检查点（服装变体、站位交叉）已由 test_compact_validator.py 等现行用例覆盖，
按 2026-10-25 决定**保留文件、不再纳入回归**（不删除，便于追溯历史行为）。

需要单独复核历史行为时仍可手动运行：
    python3 scripts/tests/test_outfit_checks.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
LEGACY = {
    "test_outfit_checks.py": "历史样本（旧四视图 fixture，早于生成轨失败关闭）",
    "test_space_sync.py": "历史样本（同上；站位检查点已由现行用例覆盖）",
}


def main() -> int:
    files = sorted(p for p in TESTS.glob("test_*.py") if p.name != "run_all.py")
    active = [p for p in files if p.name not in LEGACY]
    skipped = [p for p in files if p.name in LEGACY]

    print(f"测试目录：{TESTS}")
    print(f"纳入 {len(active)} 个文件｜跳过 {len(skipped)} 个历史样本\n")

    failed: list[tuple[str, str]] = []
    for path in active:
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        tail = (proc.stdout + proc.stderr).strip().splitlines()
        summary = next((ln for ln in reversed(tail) if ln.startswith("Ran ")), "")
        status = "OK" if proc.returncode == 0 else "FAIL"
        print(f"[{status:4}] {path.name:<38} {summary}")
        if proc.returncode != 0:
            detail = [ln for ln in tail if ln.startswith(("FAIL:", "ERROR:"))] or tail[-6:]
            failed.append((path.name, "\n".join(detail)))

    if skipped:
        print("\n未纳入（保留文件，手动可跑）：")
        for path in skipped:
            print(f"  - {path.name}：{LEGACY[path.name]}")

    print()
    if failed:
        print(f"失败 {len(failed)} 个文件：")
        for name, detail in failed:
            print(f"\n── {name} ──\n{detail}")
        return 1
    print(f"全部通过（{len(active)} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
