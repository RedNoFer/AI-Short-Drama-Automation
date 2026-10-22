#!/usr/bin/env python3
"""Resolve and verify this collection's exact source paths; no external dependencies."""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = SKILL_DIR / "references" / "catalog.json"


def load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def source_path(root, relative):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"Source path escapes resource root: {relative}")
    return candidate


def normalize_id(value):
    cleaned = value.strip().upper()
    if cleaned.startswith("S"):
        cleaned = cleaned[1:]
    if cleaned.isdigit() and 1 <= int(cleaned) <= 21:
        return f"S{int(cleaned):02d}"
    if re.fullmatch(r"E\d{2}", cleaned):
        return cleaned
    raise ValueError(f"Invalid bundle ID: {value}; use 01-21 (S01-S21) or E22-E27")


def list_bundles(catalog):
    lines = [f"{b['id']} [{b['group']}] {b['name']} — {b['select_when']}"
             for b in catalog["bundles"]]
    lines.extend(f"{e['id']} [附加] {e['name']} — {e.get('read_when', e['output'])}"
                 for e in catalog["extras"])
    return "\n".join(lines)


def dependency_status(root, dep):
    relative = dep.get("expected_path")
    if relative:
        return "现已存在，需重新检查并更新索引" if source_path(root, relative).is_file() else "未包含"
    return "未随包提供；使用前核对用户是否补充"


def resolve_bundles(catalog, root, identifiers):
    by_id = {b["id"]: b for b in catalog["bundles"]}
    extras_by_id = {e["id"]: e for e in catalog["extras"]}
    output = []
    seen = set()
    for raw in identifiers:
        key = normalize_id(raw)
        if key in seen:
            continue
        seen.add(key)
        if key.startswith("E"):
            extra = extras_by_id.get(key)
            if extra is None:
                raise ValueError(f"Unknown supplementary ID: {raw}")
            main_path = source_path(root, extra["path"])
            files = [{
                "kind": "extra", "role": "main", "label": extra["name"],
                "path": str(main_path), "exists": main_path.exists(),
                "read_when": extra.get("read_when", ""),
            }]
            for entry in extra.get("files", []):
                path = source_path(root, entry["path"])
                files.append({
                    "kind": "extra", "role": entry["role"], "label": entry["label"],
                    "path": str(path), "exists": path.is_file(),
                    "read_when": entry["read_when"],
                })
            output.append({
                "id": key, "name": extra["name"], "input": extra["input"],
                "output": extra["output"], "boundary": extra["boundary"],
                "files": files, "dependencies": [],
            })
            continue
        b = by_id[key]
        files = []
        for kind, values in (("markdown", b["markdown"]), ("companion", b["companions"])):
            for f in values:
                path = source_path(root, f["path"])
                files.append({
                    "kind": kind, "role": f["role"], "label": f["label"],
                    "path": str(path), "exists": path.is_file(), "read_when": f["read_when"],
                })
        output.append({
            "id": key, "name": b["name"], "input": b["input"], "output": b["output"],
            "boundary": b["boundary"], "files": files,
            "dependencies": [
                dict(dep, current_status=dependency_status(root, dep))
                for dep in b["dependencies"]
            ],
        })
    return output


def verify(catalog, root):
    errors = []
    bundles = catalog["bundles"]
    expected_ids = [f"S{n:02d}" for n in range(1, 22)]
    if [b["id"] for b in bundles] != expected_ids:
        errors.append("Bundle IDs must cover S01-S21 once, in order")
    group_ids = {g["id"] for g in catalog["groups"]}
    indexed_md = []
    checked_companions = []
    for b in bundles:
        if b["group"] not in group_ids:
            errors.append(f"{b['id']}: unknown group")
        directory = source_path(root, b["directory"])
        if not directory.is_dir():
            errors.append(f"Missing directory: {directory}")
        if not b["markdown"]:
            errors.append(f"{b['id']}: no Markdown entry")
        for key, values in (("markdown", b["markdown"]), ("companions", b["companions"])):
            for f in values:
                path = source_path(root, f["path"])
                if not path.is_relative_to(directory):
                    errors.append(f"{b['id']}: file assigned to wrong directory: {path}")
                if not path.is_file():
                    errors.append(f"Missing source file: {path}")
                if key == "markdown":
                    indexed_md.append(f["path"])
                    if path.suffix.lower() != ".md":
                        errors.append(f"Not Markdown: {path}")
                else:
                    checked_companions.append(f["path"])
    if len(indexed_md) != len(set(indexed_md)):
        errors.append("Duplicate source Markdown paths")
    source_md = set()
    for directory in root.iterdir():
        if directory.is_dir() and re.match(r"^(0[1-9]|1[0-9]|2[01])(?: |$)", directory.name):
            source_md.update(
                str(f.relative_to(root))
                for f in directory.rglob("*")
                if f.is_file() and f.suffix.lower() == ".md"
            )
    for rel in sorted(source_md - set(indexed_md)):
        errors.append(f"Unindexed source Markdown: {rel}")
    for rel in sorted(set(indexed_md) - source_md):
        errors.append(f"Indexed Markdown outside numbered collection: {rel}")
    for extra in catalog["extras"]:
        if not source_path(root, extra["path"]).exists():
            errors.append(f"Missing supplementary source: {extra['path']}")
        for entry in extra.get("files", []):
            if not source_path(root, entry["path"]).is_file():
                errors.append(f"Missing supplementary file: {entry['path']}")
    result = {
        "ok": not errors, "resource_root": str(root), "bundles": len(bundles),
        "indexed_source_markdown": len(indexed_md),
        "discovered_source_markdown": len(source_md),
        "checked_companions": len(checked_companions), "errors": errors,
        "known_dependencies": [
            {"bundle": b["id"], "reference": dep["reference"],
             "current_status": dependency_status(root, dep)}
            for b in bundles for dep in b["dependencies"]
        ],
    }
    return result


def md_link(label, target):
    return f"[{label}](<{target}>)"


def render_map(catalog, root):
    count = sum(len(b["markdown"]) for b in catalog["bundles"])
    lines = [
        "# 源文件精确索引", "",
        f"核对日期：{catalog['verified_on']}。资源根目录：`{root}`。",
        f"覆盖 S01–S21 共 21 组资源、{count} 个实际存在的源 Markdown；附加资源与本地补充技能见下方索引。", "",
        "本文件由 catalog.json 生成。路径有变更时先更新机器索引，再使用 locate_resources.py --render-map 重新生成；不要只改显示链接。", "",
        "MD 是创作规则/参考，TXT 中可能包含完整执行指令。PDF、示例图、视频与演示链接不能冒充 MD。", "",
        "## 分组速查", "",
        "| 组 | 模块 | 内容 |", "|---|---|---|",
    ]
    for group in catalog["groups"]:
        members = [b["id"] for b in catalog["bundles"] if b["group"] == group["id"]]
        lines.append(f"| {group['id']} | {'、'.join(members)} | {group['name']} |")
    lines.extend(["", "## 任务到文件", "",
                  "| 模块 | 资源 | 适用目标 |", "|---|---|---|"])
    for b in catalog["bundles"]:
        lines.append(f"| [{b['id']}](#{b['id'].lower()}) | {b['name']} | {b['select_when']} |")
    for b in catalog["bundles"]:
        lines.extend([
            "", f'<a id="{b["id"].lower()}"></a>', "",
            f"## {b['id']}｜{b['name']}", "",
            f"- 分组：{b['group']}。",
            f"- 输入：{b['input']}。",
            f"- 产物：{b['output']}。",
            f"- 选择条件：{b['select_when']}。",
            f"- 路由边界：{b['boundary']}", "",
            "| 源 MD 文件（绝对路径链接） | 职责 | 读取时机 |",
            "|---|---|---|",
        ])
        for f in b["markdown"]:
            path = source_path(root, f["path"])
            lines.append(
                f"| {md_link(path.name, path)} | {f['role']}：{f['label']} | {f['read_when']} |"
            )
        if b["companions"]:
            lines.extend(["", "补充文件：", "",
                          "| 文件 | 职责 | 读取时机 |", "|---|---|---|"])
            for f in b["companions"]:
                path = source_path(root, f["path"])
                lines.append(
                    f"| {md_link(path.name, path)} | {f['role']}：{f['label']} | {f['read_when']} |"
                )
        if b["dependencies"]:
            lines.extend(["", "依赖状态：", "",
                          "| 原文引用 | 当前状态 | 对使用的影响 |", "|---|---|---|"])
            for dep in b["dependencies"]:
                lines.append(
                    f"| `{dep['reference']}` | {dependency_status(root, dep)} | {dep['effect']} |"
                )
    for e in catalog["extras"]:
        lines.extend([
            "", f'<a id="{e["id"].lower()}"></a>', "",
            f"## {e['id']}｜{e['name']}", "",
            md_link(e["name"], source_path(root, e["path"])), "",
            f"- 文件类型：{e['type']}。",
            f"- 输入：{e['input']}。", f"- 产物：{e['output']}。",
            f"- 边界：{e['boundary']}。",
        ])
        if e.get("files"):
            lines.extend(["", "| 文件 | 职责 | 读取时机 |", "|---|---|---|"])
            for entry in e["files"]:
                path = source_path(root, entry["path"])
                lines.append(
                    f"| {md_link(path.name, path)} | {entry['role']}：{entry['label']} | {entry['read_when']} |"
                )
    lines.extend([
        "", "## 原配置 PDF 与示例媒体", "",
        "编号目录中的自定义GPT配置流程.pdf有18份内容相同的副本；只有配置自定义GPT时才需要阅读其中一份。",
        "PNG/MP4可用于对照布局或效果，但本索引不把示例效果视为平台当前能力或生成质量保证。",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--bundle", action="append", help="Exact ID; repeat for a workflow")
    mode.add_argument("--verify", action="store_true", help="Check paths and full source MD coverage")
    mode.add_argument("--render-map", action="store_true", help="Print generated Markdown map to stdout")
    mode.add_argument("--list", action="store_true", help="List bundle capabilities")
    parser.add_argument("--root", type=Path, help="Override resource root after moving the collection")
    args = parser.parse_args()
    catalog = load_catalog()
    inferred_root = next(
        (parent for parent in SKILL_DIR.parents
         if all((parent / catalog["bundles"][i]["directory"]).is_dir()
                for i in (0, 2, 20))),
        Path(catalog["resource_root"]),
    )
    root = (args.root or inferred_root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Resource root does not exist: {root}")
    try:
        if args.verify:
            result = verify(catalog, root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
        if args.render_map:
            result = verify(catalog, root)
            if not result["ok"]:
                print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
                return 1
            print(render_map(catalog, root), end="")
            return 0
        if args.bundle:
            result = resolve_bundles(catalog, root, args.bundle)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if all(f["exists"] for b in result for f in b["files"]) else 1
        print(list_bundles(catalog))
        return 0
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())

