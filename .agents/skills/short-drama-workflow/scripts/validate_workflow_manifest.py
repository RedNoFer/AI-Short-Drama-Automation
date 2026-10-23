#!/usr/bin/env python3
"""校验工作流清单：生成轨、评审落盘、机检命令与唯一交付包。

这是对 `validate_stage_artifacts.py` 的补充，不替代包校验器/阶段结构门。
默认检查基础项；`--strict` 额外把阶段 1 评审、阶段 4 评审内容与执行账缺失判错。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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


def has_verdict(text: str) -> bool:
    return bool(re.search(r"(通过|需修改|不通过|有条件通过)", text))


def check_review_stage1(internal: Path, strict: bool, errors: list[str], warnings: list[str]) -> None:
    path = internal / "01c-剧情评审.md"
    text = read_text(path)
    if not text.strip():
        msg = "阶段 1 评审缺失：内部/01c-剧情评审.md"
        (errors if strict else warnings).append(msg)
        return
    if len(text) < 200 or text.count("评审") < 3 or not has_verdict(text):
        msg = "阶段 1 评审内容不足：需覆盖事件/分集、逐集剧本、片段规划三次评审并含结论"
        (errors if strict else warnings).append(msg)


def check_review_stage4(internal: Path, strict: bool, errors: list[str], warnings: list[str]) -> None:
    canonical = internal / "05-提示词评审与整改.md"
    text = read_text(canonical)
    if text.strip():
        if not has_verdict(text) or not re.search(r"(评稿人|评审人|子任务|模型)", text):
            msg = "阶段 4 评审 05 缺少结论或评稿人标识"
            (errors if strict else warnings).append(msg)
        return

    a = "\n".join(read_text(p) for p in sorted(internal.glob("05a-*.md")))
    b = "\n".join(read_text(p) for p in sorted(internal.glob("05b-*.md")))
    index = read_text(internal / "05-评审索引.md")
    if a.strip() and b.strip() and index.strip():
        if "05a" not in index or "05b" not in index:
            msg = "05-评审索引.md 未同时指向 05a/05b"
            (errors if strict else warnings).append(msg)
        return
    if a.strip() and b.strip():
        msg = "阶段 4 评审为 05a/05b 分拆，但缺 05-评审索引.md"
        (errors if strict else warnings).append(msg)
        return
    msg = "阶段 4 评审缺失：内部/05-提示词评审与整改.md（或 05a/05b＋05-评审索引.md）"
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

    check_review_stage1(internal, strict, errors, warnings)
    check_review_stage4(internal, strict, errors, warnings)
    package = find_package(workdir, errors)

    return {
        "ok": not errors,
        "workdir": str(workdir),
        "branch": branch,
        "package": package.name if package else None,
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
        print(f"结果：{'通过' if result['ok'] else '失败'}（{len(result['errors'])} 错误 / {len(result['warnings'])} 提醒）")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
