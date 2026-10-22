#!/usr/bin/env python3
"""阶段出口门：每个阶段的落盘物必须齐备且自洽，缺一项即判错。

用法：
    python3 validate_stage_artifacts.py <作品目录> --stage 2
    python3 validate_stage_artifacts.py <作品目录> --stage 3
    python3 validate_stage_artifacts.py <作品目录> --stage all

为什么有这道门（2026-10-22 事故复盘）
--------------------------------------------------------------------------
上一轮《三千国道》重制时，阶段 2/3 的站位层被整段跳过，而**流水线里没有任何一道
门会因为它缺席而失败**：

  · 阶段 2/3 的落盘清单（站位基底／镜级增量／继承表）没有任何校验器检查；
  · `validate_compact_package --space-dir` 是**可选参数**，目录找不到就"跳过"；
  · 所有机检都只跑在最终交付包上，看不见上游阶段。

结果是 4 轮返工（约 50 路 agent），其中 3 轮返工的根因都是"阶段 2/3 该固化的东西
被推到了交付后"。本脚本把这些上游落盘物变成**带门的硬约束**。

判定口径
--------------------------------------------------------------------------
风险闸门（W18）：多人同框 ≥2 人／固定座位或排位／有前后排／狭小室内／
有操作位或设备承托／有人走位或离席。命中即必须建站位层。

站位层豁免：项目的 `内部/00-项目输入单.md` 写 `站位层：豁免（理由：…）` 才可跳过；
**默认必须建**。这是刻意设计成"默认要建、豁免要留痕"——反过来就等于默认可以不做。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CHARS = ("阿泽", "苏晚", "老杨", "许棠", "小林", "黑衣人")
# 通用角色名（供其他项目用）：取资产区「角色」资产名的主名
ROW = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒[，,](.*)$", re.M)
SCENE_HDR = re.compile(r"场\s*\d+-\d+")
EXEMPT_RE = re.compile(r"站位层[：:]\s*豁免")
# 阶段门豁免（仅限旧版重制等确实无法回补的项，必须写理由；每项都按提醒报出）
STAGE_EXEMPT_RE = re.compile(r"阶段门豁免[：:]\s*(.+)$", re.M)


def stage_exemptions(workdir: Path) -> set:
    """读取输入单的「阶段门豁免：」条目，返回被豁免的关键词集合。"""
    internal = workdir / "内部"
    text = ""
    for pat in ("00-*输入单*.md", "00-*.md"):
        for f in sorted(internal.glob(pat)):
            text += f.read_text(encoding="utf-8")
    out = set()
    for m in STAGE_EXEMPT_RE.finditer(text):
        for token in re.split(r"[；;、,，]", m.group(1)):
            token = token.strip()
            if not token:
                continue
            # 没写理由的豁免无效（防止豁免变成新的跳步后门）
            if "（理由" not in token and "(理由" not in token:
                continue
            out.add(re.split(r"[（(]", token, maxsplit=1)[0].strip())
    return out


# ---------------------------------------------------------------- 工具

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def char_names(workdir: Path) -> list:
    """从交付包或资产卡里取角色名。"""
    names = set(CHARS)
    for path in list(workdir.glob("精简制作包*.md")) + list((workdir / "内部").glob("*.md")):
        text = _read(path)
        for m in re.finditer(r"### 角色 ([A-Za-z0-9_]+)｜([^（\n（]+)", text):
            name = m.group(2).strip()
            if name:
                names.add(name)
    return sorted(n for n in names if len(n) >= 2)


def risk_shots_from_text(text: str, names: list) -> set:
    """文本里画内 ≥2 人的时间行集合。"""
    hits = set()
    for m in ROW.finditer(text):
        body = m.group(3)
        if sum(1 for n in names if n in body) >= 2:
            hits.add(m.group(0)[:40])
    return hits


def risk_scenes_from_script(workdir: Path, names: list) -> set:
    """剧本里 ≥2 人同场的场次 → 风险场景（用场景名做键）。"""
    script = ""
    for name in ("02-逐集拍摄剧本.md", "01-故事档案与分集规划.md", "02-资产与空间设计.md"):
        script = _read(workdir / "内部" / name)
        if script:
            break
    scenes = set()
    headers = list(re.finditer(r"### 场景 ([A-Za-z0-9_]+)｜([^\n（]*)", script))
    for m in headers:
        code = m.group(1)
        block = script[m.end():m.end() + 1200]
        if sum(1 for n in names if n in block) >= 2:
            scenes.add(code)
    if not headers:
        # 无可解析的场景头（剧本格式不同）：无法判定，按场景全算风险（宁可多要基底）
        for m in re.finditer(r"### 场景 ([A-Za-z0-9_]+)｜", script):
            scenes.add(m.group(1))
    return scenes


# ---------------------------------------------------------------- 各阶段门

def _pick(internal: Path, patterns: list) -> Path | None:
    """按模式匹配落盘物（不同项目命名不同，不能硬编码文件名）。"""
    for pat in patterns:
        hits = sorted(internal.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None


# 阶段2 必有的落盘物：语义名 → 可接受的命名模式（覆盖 0X- 两套模板命名）
STAGE2_ARTIFACTS = {
    "项目输入单": ["00-*输入单*.md", "00-*.md"],
    "故事/分集规划": ["01-*分集*.md", "01-*故事*.md", "01-*.md"],
    "剧本": ["02-*剧本*.md", "01-*剧本*.md", "02-逐集拍摄剧本.md"],
    "资产与空间设计": ["03-*资产*.md", "02-*资产*.md"],
}


def stage2(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    found: dict[str, Path] = {}
    for label, patterns in STAGE2_ARTIFACTS.items():
        path = _pick(internal, patterns)
        if path is None:
            errors.append(f"阶段2 缺少落盘物「{label}」（查找模式 {' / '.join(patterns)}）")
        else:
            found[label] = path
    # 必登内容：声线母版 / 角色美工账 / 持物链（分散在资产类文件里，合并检查）
    asset_files = sorted(
        {h for pat in ("02-*.md", "03-*.md") for h in internal.glob(pat) if h.is_file()}
        | {found[k] for k in ("资产与空间设计",) if k in found}
    )
    asset_text = "\n".join(f.read_text(encoding="utf-8") for f in asset_files)
    exempt_items = stage_exemptions(workdir)
    for kw, aliases in {
        "声线母版": ["声线母版", "声线锚点"],
        "角色美工账": ["角色美工账", "美工账"],
        "持物链": ["持物链", "持物链承接", "道具链", "持物表"],
    }.items():
        if asset_text and not any(a in asset_text for a in aliases):
            if kw in exempt_items:
                warnings.append(f"阶段2「{kw}」已登记阶段门豁免，按缺口放行")
            else:
                errors.append(f"阶段2 资产类文件缺少必登内容「{kw}」")
    # 站位层：风险场景必须各有基底
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    risk = risk_scenes_from_script(workdir, names)
    bases = sorted((internal / "04b-站位图").glob("SCENE_*.json")) if (internal / "04b-站位图").is_dir() else []
    if exempt:
        warnings.append("站位层：已按输入单登记豁免（阶段2 不要求场景基底）")
    elif risk:
        have = {b.stem.replace("SCENE_", "") for b in bases}
        missing = sorted(risk - have)
        if missing:
            exempt = stage_exemptions(workdir)
            pending = [m for m in missing if m not in exempt and "场景基底" not in exempt]
            if pending:
                errors.append(f"阶段2 站位层：风险场景缺场景基底 {pending}（命中闸门：多人同框/固定座位/前后排/狭小室内/操作位/走位）")
            else:
                warnings.append(f"阶段2 场景基底 {missing} 已登记豁免")
        for b in bases:
            try:
                doc = json.loads(b.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{b.name} JSON 解析失败：{exc}")
                continue
            for key in ("scene", "characters", "props", "camera", "lighting", "continuity"):
                if key not in doc:
                    errors.append(f"{b.name} 缺字段 {key}")
    return errors, warnings


def stage3(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    table = _pick(internal, ["04-*.md", "04-片段*.md", "分镜*.md"])
    shards: list[Path] = []
    if table is None:
        for sub in ("分镜编译", "分片", "04-分镜"):
            d = internal / sub
            if d.is_dir():
                shards = sorted(p for p in d.glob("*.md") if p.stat().st_size > 0)
                if shards:
                    break
    if table is None and not shards:
        errors.append("阶段3 缺少落盘物「片段规划与逐镜表」（查找模式 04-*.md 或 分镜编译/E*.md）")
        return errors, warnings
    text = table.read_text(encoding="utf-8") if table else "\n".join(p.read_text(encoding="utf-8") for p in shards)
    table_name = table.name if table else f"分镜编译/（{len(shards)} 集）"
    for kw, aliases in {
        "视感自查": ["视感自查"],
        "上下文衔接自查": ["上下文衔接自查", "上下文衔接"],
        "群像自检": ["群像自检", "群像自查"],
        "持物链承接": ["持物链承接", "持物链", "道具链"],
    }.items():
        if not any(a in text for a in aliases):
            if kw in stage_exemptions(workdir):
                warnings.append(f"阶段3「{kw}」已登记阶段门豁免，按缺口放行")
            else:
                errors.append(f"内部/{table_name} 缺必登内容「{kw}」")
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    risk = risk_shots_from_text(text, names)
    space = internal / "04b-站位图"
    overlays = sorted(space.glob("E*_SH*_S*.json")) if space.is_dir() else []
    if exempt:
        warnings.append("站位层：已按输入单登记豁免（阶段3 不要求镜级增量）")
    else:
        if risk and not overlays:
            errors.append(f"阶段3 站位层：风险镜头 {len(risk)} 个，但 内部/04b-站位图 下没有任何镜级增量")
        for o in overlays:
            try:
                doc = json.loads(o.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{o.name} JSON 解析失败：{exc}")
                continue
            for key in ("base", "shot", "timecode", "camera", "characters"):
                if key not in doc:
                    errors.append(f"{o.name} 缺字段 {key}")
        if (risk or overlays) and not (space / "站位继承表.md").exists():
            errors.append("阶段3 缺内部/04b-站位图/站位继承表.md（由 scripts/build_blocking_table.py 生成）")
    return errors, warnings


def stage4(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    pkgs = sorted(workdir.glob("精简制作包*.md"))
    if not pkgs:
        errors.append("阶段4 找不到交付包（精简制作包*.md）")
        return errors, warnings
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    if exempt:
        warnings.append("站位层：已按输入单登记豁免")
        return errors, warnings
    space = internal / "04b-站位图"
    overlays = list(space.glob("E*_SH*_S*.json")) if space.is_dir() else []
    for pkg in pkgs:
        text = pkg.read_text(encoding="utf-8")
        risk = risk_shots_from_text(text, names)
        if risk and not overlays:
            errors.append(
                f"{pkg.name}：命中风险闸门（{len(risk)} 个多人同框镜头）但站位层为空"
                f"（内部/04b-站位图 {'不存在' if not space.is_dir() else '无镜级增量'}）")
    return errors, warnings


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser(description="阶段出口门：检查各阶段的落盘物是否齐备")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("--stage", choices=["2", "3", "4", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    workdir = args.workdir
    if not workdir.is_dir():
        print(f"作品目录不存在：{workdir}", file=sys.stderr)
        return 2
    names = char_names(workdir)
    stages = ["2", "3", "4"] if args.stage == "all" else [args.stage]
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for st in stages:
        fn = {"2": stage2, "3": stage3, "4": stage4}[st]
        errs, warns = fn(workdir, names)
        for e in errs:
            all_errors.append(f"[阶段{st}] {e}")
        for w in warns:
            all_warnings.append(f"[阶段{st}] {w}")
    result = {"ok": not all_errors, "stage": args.stage, "errors": all_errors, "warnings": all_warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        for w in all_warnings:
            print(f"  提醒：{w}")
        for e in all_errors:
            print(f"  错误：{e}")
        print(f"\n阶段出口门：{'通过' if not all_errors else '失败'}（{len(all_errors)} 错误 / {len(all_warnings)} 提醒）")
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
