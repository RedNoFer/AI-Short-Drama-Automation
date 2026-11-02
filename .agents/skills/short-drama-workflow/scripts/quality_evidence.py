#!/usr/bin/env python3
"""派生待评清单并核对阶段2/3/4的逐项语义评审证据；不自动作出通过判断。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import workflow_common as wc

SCHEMA = "quality-evidence/1"
FILES = {"2": "03c-资产逐项验收.json", "3": "04e-逐镜空间验收.json", "4": "05b-提示词逐项验收.json"}
CHECKS = {
    "2": ("style", "identity_shape", "internal_consistency"),
    "scene": ("topology", "support_initial_state"),
    "3": ("physical_space", "cast_visibility", "prop_state", "entry_exit"),
    "4": ("current_clip_only", "visual_inheritance", "space_state", "reference_binding", "subtitle_policy", "entry_exit"),
}


def _pick(root: Path, patterns: tuple[str, ...]) -> Path:
    for pattern in patterns:
        found = sorted(p for p in root.glob(pattern) if p.is_file() and p.stat().st_size)
        if found:
            return found[0]
    raise ValueError(f"缺少上游文件：{' / '.join(patterns)}")


def scope(workdir: Path, stage: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """清单取实际资产/分镜/提示词，禁止评审者手填范围来隐藏漏项。"""
    import scaffold_segment as scaffold
    import validate_compact_package as compact

    internal = workdir / "内部"
    brief = _pick(internal, ("00-项目输入单.md", "00-*输入单*.md"))
    master = _pick(internal, ("03-资产与空间设计.md", "03-*.md", "02-资产*.md"))
    assets = _pick(internal, ("03a-固定资产图片提示词.md",))
    paths = {brief, master, assets}
    items: dict[str, list[str]] = {}
    space = internal / "04b-站位图"
    paths.update(space.glob("SCENE_*.json"))
    if stage == "2":
        for kind, code in re.findall(r"^### (角色|场景|道具|线索) ([A-Za-z][A-Za-z0-9_-]*)｜", assets.read_text(), re.M):
            if code in items:
                raise ValueError(f"资产验收清单重复：{code}")
            items[code] = list(CHECKS["2"]) + (list(CHECKS["scene"]) if kind == "场景" else [])
    else:
        board = _pick(internal, ("04-片段规划与逐镜表.md", "04-*.md"))
        facts = _pick(internal, ("04c-衔接事实.json",))
        paths.update((board, facts))
        paths.update(space.glob("E*_SH*_S*.json"))
        if stage == "3":
            for sid, block in wc.split_segments(board.read_text()):
                rows = scaffold.parse_table(block)
                if not rows:
                    raise ValueError(f"{sid} 缺实际逐镜表，不允许漏出验收范围")
                for row in rows:
                    number = re.fullmatch(r"S?(\d+)", row["shot"].strip(), re.I)
                    if not number:
                        raise ValueError(f"镜号不能派生验收范围：{sid}/{row['shot']}")
                    key = f"{sid}-S{int(number[1]):02d}"
                    if key in items:
                        raise ValueError(f"逐镜验收清单重复：{key}")
                    items[key] = list(CHECKS["3"])
        else:
            package = workdir / "精简制作包.md"
            if not package.is_file():
                raise ValueError("缺少精简制作包.md")
            paths.add(package)
            parsed = compact.parse_structure(package.read_text())
            if parsed["errors"]:
                raise ValueError("制作包结构错误，不能派生提示词验收范围：" + "；".join(parsed["errors"][:3]))
            for episode in parsed["episodes"]:
                for shot in episode["shots"]:
                    key = wc.normalize_seg_id(f"{episode['code']}-{shot['code']}")
                    if key in items:
                        raise ValueError(f"提示词验收清单重复：{key}")
                    items[key] = list(CHECKS["4"])
    if not items:
        raise ValueError("无法从实际上游产物派生任何验收项，不允许用空清单放行")
    inputs = {str(p.relative_to(workdir)): wc.sha256_file(p) for p in sorted(paths)}
    inputs["@policy.json"] = wc.sha256_file(wc.POLICY_PATH)
    return inputs, items


def initialize(workdir: Path, stage: str) -> dict:
    inputs, items = scope(workdir, stage)
    return {
        "schema": SCHEMA, "stage": stage,
        "authors": [], "reviewer": {"id": "", "independent": False},
        "inputs": inputs, "image_review": "pending", "defects": [],
        "items": [{"id": key, "checks": {name: {
            "status": "pending", "finding": "", "evidence": []
        } for name in names}} for key, names in items.items()],
    }


def check(workdir: Path, stage: str) -> list[str]:
    path = workdir / "内部" / FILES[stage]
    if not path.is_file():
        return [f"缺逐项语义验收证据 {path.name}（quality_evidence.py --stage {stage} --init 仅生成待评骨架）"]
    try:
        required_inputs, wanted = scope(workdir, stage)
        doc = json.loads(path.read_text())
    except (OSError, ValueError, TypeError) as exc:
        return [f"逐项验收不可读取：{exc}"]
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or doc.get("stage") != stage:
        return [f"{path.name} schema/stage 不匹配"]
    errors: list[str] = []
    reviewer = doc.get("reviewer")
    authors = doc.get("authors")
    if (not isinstance(reviewer, dict) or not isinstance(authors, list) or not authors
            or not all(isinstance(a, str) and a.strip() for a in authors)
            or not isinstance(reviewer.get("id"), str) or not reviewer["id"].strip()
            or reviewer.get("independent") is not True
            or reviewer["id"].strip() in [a.strip() for a in authors]):
        errors.append("作者与独立评审人须实名登记为不同执行者；不能由起草人自行签通过")
    inputs = doc.get("inputs")
    texts: dict[str, str] = {}
    if not isinstance(inputs, dict):
        return errors + ["验收缺 inputs 版本锁"]
    for rel, digest in required_inputs.items():
        if inputs.get(rel) != digest:
            errors.append(f"验收漏锁或版本过期：{rel}")
    for rel, digest in inputs.items():
        if rel == "@policy.json":
            continue
        if not isinstance(rel, str):
            errors.append("inputs 路径必须是字符串")
            continue
        source = (workdir / rel).resolve()
        if not source.is_relative_to(workdir.resolve()) or not source.is_file():
            errors.append(f"证据文件不在项目内或不存在：{rel}")
            continue
        if wc.sha256_file(source) != digest:
            errors.append(f"验收证据版本已变化：{rel}")
        try:
            texts[rel] = source.read_text()
        except UnicodeError:
            pass  # 实际图片可锁哈希，但不能冒充文本引文已目检。
    if not isinstance(doc.get("image_review"), str) or doc["image_review"] not in {"pending", "checked", "not_applicable"}:
        errors.append("image_review 必须声明 pending/checked/not_applicable，文字通过不等于图像通过")
    if doc.get("image_review") == "checked" and not any(
        isinstance(rel, str) and Path(rel).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".avif"}
        for rel in inputs
    ):
        errors.append("声称图像已检查却未锁定任何实际图片；没有图时只能标 pending")
    defects = doc.get("defects")
    if not isinstance(defects, list):
        errors.append("缺 defects 清单（无缺陷用 []）")
    else:
        for defect in defects:
            if (not isinstance(defect, dict) or defect.get("status") != "closed"
                    or not isinstance(defect.get("resolution"), str) or not defect["resolution"].strip()):
                errors.append("存在未关闭或无整改证据的缺陷")
    rows = doc.get("items")
    if not isinstance(rows, list) or not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in rows):
        return errors + ["items 必须是逐项验收对象列表"]
    got: dict[str, dict] = {}
    for row in rows:
        if row["id"] in got:
            errors.append(f"验收项重复：{row['id']}")
        got[row["id"]] = row
    if set(got) != set(wanted):
        errors.append(f"验收范围不完整：缺 {sorted(set(wanted) - set(got))}；多 {sorted(set(got) - set(wanted))}")
    for key, names in wanted.items():
        checks = got.get(key, {}).get("checks")
        if not isinstance(checks, dict):
            errors.append(f"{key} 缺逐项检查")
            continue
        for name in names:
            item = checks.get(name)
            label = f"{key}/{name}"
            if (not isinstance(item, dict) or not isinstance(item.get("status"), str)
                    or item["status"] not in {"pass", "not_applicable"}):
                errors.append(f"{label} 未通过／未评审")
                continue
            if not isinstance(item.get("finding"), str) or not item["finding"].strip():
                errors.append(f"{label} 缺具体判断；不适用项也须说明原因")
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{label} 缺指向已锁版本原文的证据")
                continue
            for ev in evidence:
                if (not isinstance(ev, dict) or not isinstance(ev.get("file"), str)
                        or not isinstance(ev.get("quote"), str) or not ev["quote"].strip()
                        or ev["file"] not in texts or ev["quote"] not in texts[ev["file"]]):
                    errors.append(f"{label} 证据引文不存在或未锁版本")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--stage", choices=FILES, required=True)
    parser.add_argument("--init", action="store_true")
    args = parser.parse_args()
    root = args.workdir.resolve()
    try:
        if args.init:
            path = root / "内部" / FILES[args.stage]
            if path.exists():
                raise ValueError(f"{path.name} 已存在，不覆盖旧评审；先复核受影响项")
            data = initialize(root, args.stage)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"已生成待评清单：{path}；没有任何条目自动通过")
            return 0
        errors = check(root, args.stage)
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"错误：{error}")
    print(f"逐项证据门：{'失败' if errors else '通过'}（仅检查证据完整性、版本及覆盖，不代替语义判断）")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
