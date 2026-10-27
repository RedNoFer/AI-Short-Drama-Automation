#!/usr/bin/env python3
"""校验工作流清单：生成轨、评审落盘、机检命令与唯一交付包。

这是对 `validate_stage_artifacts.py` 的补充，不替代包校验器/阶段结构门。
默认检查基础项；`--strict` 额外把阶段 1 评审、阶段 4 评审内容与执行账缺失判错。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_common as wc
from validate_compact_package import parse_structure

BRANCHES = ("seedance25", "wan30", "h3")
LABEL_TO_BRANCH = {
    "seedance 2.5": "seedance25",
    "seedance2.5": "seedance25",
    "wan3.0": "wan30",
    "wan 3.0": "wan30",
    "minimax h3": "h3",
    "minimaxh3": "h3",
}
BACKUP_MARKERS = ("备份", "整改前", "重制前", "backup")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def detect_branch(text: str) -> tuple[str | None, list[str]]:
    found: list[str] = []
    for match in re.finditer(r"--model\s+(seedance25|wan30|h3)\b", text, re.I):
        found.append(match.group(1).lower())
    if not found:
        for match in re.finditer(
            r"(?:目标生成模型轨|生成模型轨|生成轨|模型轨|生成模型)\s*[|:：]\s*[^\n]{0,100}?"
            r"(seedance25|wan30|h3)\b",
            text,
            re.I,
        ):
            found.append(match.group(1).lower())
    if not found:
        for label, branch in LABEL_TO_BRANCH.items():
            if re.search(re.escape(label), text, re.I):
                found.append(branch)
    unique = list(dict.fromkeys(found))
    if len(unique) == 1:
        return unique[0], []
    if len(unique) > 1:
        return None, [f"输入单出现多个生成轨候选：{', '.join(unique)}；一个项目只能登记一个"]
    return None, ["输入单未识别到生成轨（seedance25 / wan30 / h3）"]


def has_pass_verdict(text: str) -> bool:
    """只把明确写成「通过」的结论视为放行；有问题/需修改不是有效放行。"""
    return bool(re.search(
        r"^\s*(?:[-*]\s*)?(?:(?:总体|阶段\s*\d+放行|评审)\s*)?结论\s*[：:]\s*通过(?:\s*[，,。；;]|$)",
        text, re.M))


def _section_text(text: str, label: str) -> str:
    return wc.markdown_section(text, label)


def _section_pass(text: str, label: str) -> bool:
    section = _section_text(text, label)
    match = re.search(r"^\s*(?:[-*]\s*)?结论\s*[：:]\s*([^\n。；;，,]+)", section, re.M)
    return bool(match and match.group(1).strip() == "通过")


def _package_prompt_hashes(package: Path | None) -> tuple[dict[str, str], list[str]]:
    """读最终包的 episode/segment 字段，计算每条视频提示词正文的 SHA-256。"""
    if package is None or not package.is_file():
        return {}, ["缺少精简制作包，无法核对阶段 4 全覆盖评审"]
    parsed = parse_structure(read_text(package))
    errors = [f"制作包结构：{issue}" for issue in parsed["errors"]]
    hashes: dict[str, str] = {}
    for episode in parsed["episodes"]:
        for shot in episode["shots"]:
            segment_id = f"{episode['code']}-{shot['code']}"
            if segment_id in hashes:
                errors.append(f"制作包片段 ID 重复：{segment_id}")
                continue
            prompt = shot["prompts"].get("视频提示词")
            if prompt is None or not prompt.strip():
                errors.append(f"制作包片段 {segment_id} 缺少可计算的「视频提示词」text 块")
                continue
            hashes[segment_id] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if not hashes and not errors:
        errors.append("制作包未提取到任何片段提示词，不能证明全覆盖")
    return hashes, errors


def _review_hash_coverage(report: str, expected: dict[str, str]) -> list[str]:
    return wc.review_row_errors(report, expected)


def _review_release_errors(report: str, label: str, reviewer_required: bool = True) -> list[str]:
    """The current global summary, not an old/local verdict, controls stage release."""
    summary = wc.markdown_section(report, "全局汇总") or report
    verdicts = re.findall(
        r"^\s*(?:[-*]\s*)?(?:(?:总体|整体|总评|评审)\s*)?结论\s*[：:]\s*([^\n。；;，,]+)", summary, re.M)
    counts = re.findall(r"^\s*(?:[-*]\s*)?未关闭阻断/重要缺陷\s*[：:]\s*(\d+)\s*$", summary, re.M)
    errors = []
    if not verdicts or any(verdict.strip() != "通过" for verdict in verdicts):
        errors.append(f"阶段 4 {label} 必须明确写「结论：通过」，且全局汇总不得含冲突结论")
    if not counts or any(int(count) != 0 for count in counts):
        errors.append(f"阶段 4 {label} 必须明确写「未关闭阻断/重要缺陷：0」")
    if reviewer_required and not re.search(r"(评稿人|评审人|子任务|模型)", report):
        errors.append(f"阶段 4 {label} 未标明独立评审人")
    return errors


def check_review_stage1(internal: Path, strict: bool, errors: list[str], warnings: list[str]) -> None:
    path = internal / "01c-剧情评审.md"
    text = read_text(path)
    if not text.strip():
        msg = "阶段 1 评审缺失：内部/01c-剧情评审.md"
        (errors if strict else warnings).append(msg)
        return
    checkpoints = ("事件/分集", "逐集剧本", "片段规划")
    missing = [label for label in checkpoints if not _section_pass(text, label)]
    if len(text) < 200 or missing:
        detail = "、".join(missing) if missing else "评审正文不足"
        msg = f"阶段 1 评审未能证明三个交接点均通过：{detail}"
        (errors if strict else warnings).append(msg)


def check_review_stage4(internal: Path, package: Path | None, strict: bool,
                       errors: list[str], warnings: list[str]) -> None:
    expected_hashes, hash_errors = _package_prompt_hashes(package)
    canonical = internal / "05-提示词评审与整改.md"
    text = read_text(canonical)
    if text.strip():
        for issue in (_review_release_errors(text, "评审 05") + hash_errors
                      + _review_hash_coverage(text, expected_hashes)):
            (errors if strict else warnings).append(issue)
        return

    candidates = [p for p in sorted(internal.glob("05*-*.md"))
                  if re.match(r"05[a-z]+-", p.name)]
    index = read_text(internal / "05-评审索引.md")
    if index.strip():
        # Read only reports listed in the index; archived/unlisted drafts do not
        # invalidate an accepted review. Legacy 05a/05b prefix links remain valid.
        selected = [p for p in candidates if p.name in index or re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(p.name.split('-')[0])}(?![A-Za-z0-9_-])", index)]
        reports = [(p.name, read_text(p)) for p in selected]
        referenced = set(re.findall(r"\b05[a-z]+\b", index))
        missing = referenced - {p.name.split('-')[0] for p in selected}
        issues = [f"05-评审索引.md 引用的评审不存在：{name}" for name in sorted(missing)]
        if not reports:
            issues.append("05-评审索引.md 未指向任何有效的分拆评审文件")
        for label, report in reports + [("评审索引", index)]:
            issues.extend(_review_release_errors(report, label, reviewer_required=label != "评审索引"))
        # The index routes reports; its optional digest summary is not a second review.
        combined = "\n".join(report for _, report in reports)
        for issue in issues + hash_errors + _review_hash_coverage(combined, expected_hashes):
            (errors if strict else warnings).append(issue)
        return
    if candidates:
        msg = "阶段 4 评审已分拆，但缺 05-评审索引.md"
        (errors if strict else warnings).append(msg)
        return
    msg = "阶段 4 评审缺失：内部/05-提示词评审与整改.md（或索引列出的分拆报告＋05-评审索引.md）"
    (errors if strict else warnings).append(msg)


def check_gate_output(internal: Path, branch: str, errors: list[str], warnings: list[str]) -> None:
    path = internal / "06-机检结果.txt"
    text = read_text(path)
    if not text.strip():
        errors.append("阶段 5 机检记录缺失：内部/06-机检结果.txt")
        return
    if "validate_compact_package" not in text:
        errors.append("06-机检结果.txt 未记录 validate_compact_package 运行结果")
    models = re.findall(r"--model\s+(seedance25|wan30|h3)\b", text, re.I)
    if models:
        wrong = sorted({m.lower() for m in models} - {branch})
        if wrong:
            errors.append(f"06 机检命令的模型轨 {wrong} 与输入单登记轨 {branch} 不一致")
    elif branch in ("wan30", "h3"):
        errors.append(f"06 机检命令缺少与登记轨一致的 --model {branch}")
    elif branch == "seedance25" and "--tier" not in text:
        warnings.append("06 未记录 --tier；Seedance 2.5 轨应写明所用档位")


def check_ledger(internal: Path, branch: str, strict: bool, errors: list[str], warnings: list[str]) -> None:
    path = internal / "执行账.md"
    text = read_text(path)
    if not text.strip():
        msg = "执行账缺失：内部/执行账.md"
        (errors if strict else warnings).append(msg)
        return
    if branch not in text:
        msg = f"执行账未写明生成轨 {branch}"
        (errors if strict else warnings).append(msg)
    if "阶段" not in text:
        msg = "执行账未见阶段记录"
        (errors if strict else warnings).append(msg)


def find_package(workdir: Path, errors: list[str]) -> Path | None:
    packages = [
        p for p in workdir.glob("精简制作包*.md")
        if not any(marker in p.name for marker in BACKUP_MARKERS)
    ]
    if not packages:
        errors.append("未找到非备份精简制作包：精简制作包*.md")
        return None
    if len(packages) > 1:
        errors.append("存在多个非备份精简制作包：" + "、".join(p.name for p in packages))
        return None
    return packages[0]


def validate(workdir: Path, strict: bool = False) -> dict:
    internal = workdir / "内部"
    errors: list[str] = []
    warnings: list[str] = []

    brief = internal / "00-项目输入单.md"
    brief_text = read_text(brief)
    if not brief_text.strip():
        errors.append("输入单缺失：内部/00-项目输入单.md")
        branch = None
    else:
        branch, branch_issues = detect_branch(brief_text)
        for issue in branch_issues:
            errors.append(issue)

    if branch:
        check_gate_output(internal, branch, errors, warnings)
        check_ledger(internal, branch, strict, errors, warnings)

    package = find_package(workdir, errors)
    check_review_stage1(internal, strict, errors, warnings)
    check_review_stage4(internal, package, strict, errors, warnings)
    prompt_hashes, _ = _package_prompt_hashes(package)

    return {
        "ok": not errors,
        "workdir": str(workdir),
        "branch": branch,
        "package": package.name if package else None,
        "expected_prompt_sha256": prompt_hashes,
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验短剧工作流清单与分支一致性")
    parser.add_argument("workdir", type=Path, help="作品目录，例如 创作输出/作品名")
    parser.add_argument("--strict", action="store_true",
                        help="把阶段 1/4 评审内容与执行账缺失判为错误")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = validate(args.workdir, strict=args.strict)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"工作流清单：{result['workdir']}")
        print(f"生成轨：{result['branch'] or '未识别'}｜包：{result['package'] or '缺失'}｜模式：{'strict' if args.strict else '基础'}")
        for item in result["errors"]:
            print(f"错误：{item}")
        for item in result["warnings"]:
            print(f"提醒：{item}")
        if result["expected_prompt_sha256"]:
            print("当前包提示词正文 SHA-256（用于阶段4评审覆盖表）：")
            for segment_id, digest in result["expected_prompt_sha256"].items():
                print(f"  {segment_id}  {digest}")
        print(f"结果：{'通过' if result['ok'] else '失败'}（{len(result['errors'])} 错误 / {len(result['warnings'])} 提醒）")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
