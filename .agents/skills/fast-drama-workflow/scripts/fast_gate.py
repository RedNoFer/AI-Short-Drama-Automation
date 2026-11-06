#!/usr/bin/env python3
"""快速生产（Wan3.0 快速档）合并机检：一条命令跑完全部校验器，输出硬错/风险两栏报告。

只封装完全体既有校验器，不复制其校验逻辑：
1. validate_compact_package.py <pkg> --model wan30 —— 结构硬错
2. audit_wan30_antipatterns.py <pkg> --json       —— 反例模式
3. validate_novel_coverage.py <pkg> <novel>       —— 原文覆盖（--novel 缺省则 SKIP）

第 0 步本地预检：已登记规则的存在性机检——
1. R39/TEXT-03：含台词或心声的提示词块缺 `画面文字纪律：` 统一句即为硬错；
2. 否定写法纪律（wan30-adapter §4.2 第 7 块）：视频/图片提示词正文出现
   「不在画面／不入画／不出镜／未出镜」类具象名词否定句即为硬错。
待完全体校验器回填上述项后移除对应预检。

硬错 = 必须修复后重跑（秒级迭代）；风险 = 一句话结论，合评时给理由即可。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "short-drama-workflow" / "scripts"

PROMPT_BLOCK_RE = re.compile(r"####\s*视频提示词\s*\n+```text\n(.*?)```", re.S)
IMAGE_BLOCK_RE = re.compile(r"####\s*图片提示词\s*\n+```text\n(.*?)```", re.S)
DIALOGUE_HINT_RE = re.compile(r'["“].*["”]', re.S)
SPEECH_MARKER_RE = re.compile(r"口型|画外|心声|对白（|对白:")
TEXT_DISCIPLINE_RE = re.compile(r"^\s*画面文字纪律[：:]", re.M)
# 否定写法纪律（wan30-adapter §4.2 第 7 块）：正文点名被排除物＝给概念加权。
NEGATION_PHRASE_RE = re.compile(r"不在画面|不出现在画面|不入画|不出镜|未出镜")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """执行子进程，返回 (returncode, stdout, stderr)。报告脚本缺失为硬错。"""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as exc:
        return 127, "", f"脚本缺失：{exc}"


def _r39_check(pkg: Path) -> list[dict]:
    """R39/TEXT-03 预检：含台词或心声的提示词块须含画面文字纪律统一句。"""
    issues: list[dict] = []
    try:
        text = pkg.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [{"kind": "r39_preflight_io", "segment": str(pkg), "detail": str(exc)}]
    for match in PROMPT_BLOCK_RE.finditer(text):
        body = match.group(1)
        has_speech = bool(SPEECH_MARKER_RE.search(body)) and bool(
            DIALOGUE_HINT_RE.search(body)
        )
        if has_speech and not TEXT_DISCIPLINE_RE.search(body):
            start = text.count("\n", 0, match.start()) + 1
            issues.append(
                {
                    "kind": "missing_text_discipline_line",
                    "segment": f"约第 {start} 行提示词块",
                    "detail": "含台词/心声但缺 `画面文字纪律：` 统一句（R39/TEXT-03）",
                }
            )
    return issues


def _negation_check(pkg: Path) -> list[dict]:
    """否定写法纪律预检：提示词正文出现具象名词否定句即为硬错。

    生成模型对否定词低敏感、具象名词每多出现一次显著度递增
    （实机案例：正文两处「南瓜不在画面内」反致南瓜入画）。
    排除一律改正向白名单；被排除物来自参考图时改图不改字。
    """
    issues: list[dict] = []
    try:
        text = pkg.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [{"kind": "negation_preflight_io", "segment": str(pkg), "detail": str(exc)}]
    for block_re, label in (
        (PROMPT_BLOCK_RE, "视频提示词"),
        (IMAGE_BLOCK_RE, "图片提示词"),
    ):
        for match in block_re.finditer(text):
            body = match.group(1)
            for hit in NEGATION_PHRASE_RE.finditer(body):
                start = text.count("\n", 0, match.start()) + 1
                ctx_l = max(0, hit.start() - 12)
                context = body[ctx_l:hit.end() + 12].replace("\n", " ")
                issues.append(
                    {
                        "kind": "negation_object_denial",
                        "segment": f"约第 {start} 行{label}块",
                        "detail": (
                            f"正文出现具象名词否定「…{context}…」——按 wan30-adapter "
                            "§4.2 第 7 块改正向白名单（只写有什么，不点名被排除物）；"
                            "被排除物来自参考图时改图不改字"
                        ),
                    }
                )
    return issues


def _fmt_issues(items: list[dict], limit: int = 12) -> list[str]:
    out = []
    for item in items[:limit]:
        detail = str(item.get("detail", ""))[:200]
        out.append(f"  - {item.get('kind', '?')}｜{item.get('segment', '')}｜{detail}")
    if len(items) > limit:
        out.append(f"  - …另 {len(items) - limit} 条同类硬错")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="快速档合并机检：结构＋反例＋覆盖＋R39 预检，一次跑完。"
    )
    parser.add_argument("package", type=Path, help="精简制作包 Markdown 文件")
    parser.add_argument("--novel", type=Path, default=None, help="源小说原文（可选）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args()

    report: dict = {"package": str(args.package), "hard_errors": [], "risks": [], "skipped": []}

    if not args.package.exists():
        print(f"找不到文件：{args.package}", file=sys.stderr)
        return 2

    # 第 0 步：R39/TEXT-03 预检
    r39_issues = _r39_check(args.package)
    if r39_issues:
        report["hard_errors"].append({"step": "0 文字纪律预检", "items": r39_issues})

    # 第 0 步：否定写法纪律预检
    neg_issues = _negation_check(args.package)
    if neg_issues:
        report["hard_errors"].append({"step": "0 否定写法预检", "items": neg_issues})

    # 第 1 步：结构校验
    rc, out, err = _run(
        [sys.executable, str(SCRIPTS_DIR / "validate_compact_package.py"),
         str(args.package), "--model", "wan30"]
    )
    full_out = (out or err)
    errors_i = [ln.strip() for ln in full_out.splitlines() if "错误：" in ln]
    warn_i = [ln.strip() for ln in full_out.splitlines() if "提醒：" in ln]

    def _mk_item(line: str) -> dict:
        m = re.match(r"错误：([^:：]+)：?\s*(.*)", line)
        if m:
            return {"kind": "validator_error", "segment": m.group(1),
                    "detail": m.group(2).lstrip("：: ")}
        return {"kind": "validator_error", "segment": "", "detail": line}

    if rc != 0:
        if errors_i:
            report["hard_errors"].append(
                {"step": "1 结构校验", "returncode": rc,
                 "items": [_mk_item(e) for e in errors_i]}
            )
        else:  # 非预期失败（无结构化错误行）：回退截尾展示
            tail = full_out.strip().splitlines()[-8:]
            report["hard_errors"].append(
                {"step": "1 结构校验", "returncode": rc,
                 "items": [{"detail": " ".join(tail)[:400]}]}
            )
    else:
        last = full_out.strip().splitlines()[-1:] or [""]
        report["structure_summary"] = last[0]
    if warn_i:
        report["risks"].extend(warn_i)

    # 第 2 步：反例审计
    rc, out, err = _run(
        [sys.executable, str(SCRIPTS_DIR / "audit_wan30_antipatterns.py"),
         str(args.package), "--json"]
    )
    audit: dict = {}
    if rc == 127:
        report["hard_errors"].append(
            {"step": "2 反例审计", "items": [{"detail": err or "脚本缺失"}]}
        )
    elif rc not in (0,):
        report["hard_errors"].append(
            {"step": "2 反例审计", "items": [{"detail": (err or out).strip()[-300:]}]}
        )
    else:
        try:
            audit = json.loads(out)
        except json.JSONDecodeError:
            report["hard_errors"].append(
                {"step": "2 反例审计", "items": [{"detail": "JSON 解析失败"}]}
            )
        else:
            hard = [i for i in audit.get("issues", []) if i.get("level") == "error"]
            warns = [i for i in audit.get("issues", []) if i.get("level") == "warning"]
            if hard:
                report["hard_errors"].append({"step": "2 反例审计", "items": hard})
            by_kind: dict[str, int] = {}
            for w in warns:
                by_kind[w.get("kind", "?")] = by_kind.get(w.get("kind", "?"), 0) + 1
            report["risks"].append(
                {"step": "2 反例审计", "counts": by_kind,
                 "note": "一句话结论即可，合评第 10 项核对处置理由；不强制清零"}
            )
            report["audit_summary"] = {
                "segments": audit.get("segments"),
                "rows": audit.get("rows"),
                "camera_missing_prefix": audit.get("camera_missing_prefix"),
                "no_gaze_segments": audit.get("no_gaze_segments"),
            }

    # 第 3 步：原文覆盖
    if args.novel is None:
        report["skipped"].append("3 覆盖率：未给 --novel，跳过（交付说明需注明）")
    elif not args.novel.exists():
        report["hard_errors"].append(
            {"step": "3 覆盖率", "items": [{"detail": f"找不到小说文件：{args.novel}"}]}
        )
    else:
        rc, out, err = _run(
            [sys.executable, str(SCRIPTS_DIR / "validate_novel_coverage.py"),
             str(args.package), str(args.novel)]
        )
        if rc != 0:
            tail = (err or out).strip().splitlines()[-6:]
            report["hard_errors"].append(
                {"step": "3 覆盖率", "returncode": rc,
                 "items": [{"detail": " ".join(tail)[:400]}]}
            )
        else:
            last = (out or err).strip().splitlines()[-1:] or [""]
            report["coverage_summary"] = last[0]

    if bool(args.json):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 68)
        print(f"快速档合并机检｜{args.package}")
        print("=" * 68)
        if report.get("structure_summary"):
            print(f"[1] 结构校验：{report['structure_summary']}")
        if report.get("audit_summary"):
            s = report["audit_summary"]
            print(
                f"[2] 反例审计：段数 {s.get('segments')}｜时间行 {s.get('rows')}"
                f"｜镜头未前置 {s.get('camera_missing_prefix')}｜缺「不看镜头」段 {s.get('no_gaze_segments')}"
            )
        if "3 覆盖率：未给 --novel，跳过（交付说明需注明）" in report["skipped"]:
            print("[3] 覆盖率：SKIP（未给 --novel）")
        elif report.get("coverage_summary"):
            print(f"[3] 覆盖率：{report['coverage_summary']}")
        if report["risks"]:
            print("\n风险（合评给理由即可，不强制清零）：")
            for risk in report["risks"]:
                if isinstance(risk, str):
                    print(f"  - {risk[:180]}")
                else:
                    for kind, n in sorted(risk.get("counts", {}).items()):
                        print(f"  - {kind} ×{n}")
        if report["hard_errors"]:
            print("\n硬错（必须修复后重跑本命令）：")
            for block in report["hard_errors"]:
                step = block.get("step", "?")
                for line in _fmt_issues(block.get("items", [])):
                    print(line)
            print(f"\n结论：{sum(len(b.get('items', [])) for b in report['hard_errors'])} 条硬错，"
                  "清零前不得合评/交付。")
            return 1
        print("\n结论：硬错为零，可进入合评清单（lean-checks.md）。")

    return 1 if report["hard_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
