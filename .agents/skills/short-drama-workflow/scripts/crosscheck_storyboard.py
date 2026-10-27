#!/usr/bin/env python3
"""分镜视感自查交叉校验：把「声明值」和「逐镜表实算值」对上。

为什么有这个脚本（2026-10-23 审计）
--------------------------------------------------------------------------
小墨 6.3 的视感配额（固定镜头≤10%、焦段≥4 种、机位角度≥6 种、禁连续固定、
景别不连三近景）以前只写在散文式自查里，由 agent 手算、由评审事后复核。
后果和 PROC-05 同型：**统计错了没人知道，声明和事实不一致也没人知道**，
过去只能等到交付末尾再靠人重读；现已前移到阶段 3 出口门，在提示词开工前发现视感统计与逐镜表不一致。

本脚本把可机械统计的部分前移到阶段 3 出口门：
  · 声明值 vs 实算值不一致 → 判错（阻断）；
  · 配额超限 → 判错；
  · 逐镜表缺列、景别/焦段不可识别 → 判错（格式不成立就没法校验）。

口径与格式定义见 references/storyboard-selfcheck.md。
本脚本不判断「运镜有没有叙事职责」「景别是否服务剧情」，那是独立评审的职责。

用法：
    crosscheck_storyboard.py <分镜文件> [--tier tier2_xiaomo63] [--emit] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SIZES = ["大特写", "大远景", "中近景", "特写", "近景", "中景", "全景", "远景"]
CLOSE_SIZES = {"中近景", "近景", "特写", "大特写"}
ENV_SIZES = {"大远景", "远景"}
FIXED_WORDS = ("固定", "静止", "不动", "机位不动")
FIXED_ESCAPE = ("重锤", "留白", "凝固")
STAT_RE = re.compile(r"视感统计\s*[：:]\s*(.+)")
SEP_RE = re.compile(r"^[\s|:\-—]+$")
HEADER_KEYS = {
    "景别": ("景别", "镜头景别"),
    "焦段": ("焦段", "焦距"),
    "机位": ("机位", "机位角度"),
    "运镜": ("运镜", "镜头运动"),
}
OPTIONAL_KEYS = {
    "镜": ("镜", "镜号", "镜头", "shot"),
    "固定": ("固定", "是否固定"),
    "景深": ("景深",),
    "片段": ("片段",),
    "备注": ("备注", "说明"),
}
REQUIRED_STATS = ["镜数", "固定", "固定占比", "焦段种数", "机位角度种数", "侧45占比"]
SEGMENT_HEADING_RE = re.compile(
    r"^(#{2,6})\s+.*?(?:E\d{2}[-_]SH\d{2}|C\d{2})(?=$|[\s｜|])", re.M)
SEGMENT_ID_RE = re.compile(r"(E\d{2}[-_]SH\d{2}|C\d{2})(?=$|[\s｜|])")


# ---------------------------------------------------------------- 解析

def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def _norm(text: str) -> str:
    return (text or "").replace("　", " ").replace("°", "").replace(" ", "").strip()


def _find_col(header: list[str], names: tuple) -> int | None:
    """先精确匹配列名，再退化为包含匹配（避免「段」误吃「焦段」）。"""
    for i, cell in enumerate(header):
        low = cell.casefold().strip()
        for name in names:
            if low == name.casefold():
                return i
    for i, cell in enumerate(header):
        low = cell.casefold()
        for name in names:
            if name.casefold() in low:
                return i
    return None


def _size(cell: str) -> str:
    text = _norm(cell)
    for size in SIZES:
        if size in text:
            return size
    return ""


def _focal(cell: str) -> int | None:
    match = re.search(r"(\d{2,3})\s*(?:mm|毫米)?", _norm(cell), re.I)
    return int(match.group(1)) if match else None


def _is_fixed(move: str, flag: str) -> bool:
    text = _norm(flag)
    if text:
        if text in ("否", "n", "no", "-", "—"):
            return False
        if any(word in text for word in ("是", "固定", "静止", "重锤", "留白", "凝固")):
            return True
    motion = _norm(move)
    if not motion:
        return False
    # 「静止一秒后每秒约 2 度漂移」「固定起幅后横移」不是固定镜：
    # 运镜里出现任何位移动词时，不能仅凭「静止/固定」二字判为固定。
    if any(word in motion for word in ("推", "拉", "摇", "移", "跟", "漂", "升降", "环绕", "变焦")):
        return False
    return any(word in motion for word in FIXED_WORDS) and "微" not in motion


def _is_escape(flag: str, move: str, note: str) -> bool:
    text = _norm(flag) + _norm(move) + _norm(note)
    return any(word in text for word in FIXED_ESCAPE)


def parse_shots(text: str) -> tuple[list[dict], list[str]]:
    """解析所有含 景别/焦段/机位/运镜 四列的表格行。"""
    errors: list[str] = []
    shots: list[dict] = []
    lines = text.replace("\r\n", "\n").split("\n")
    heading = ""
    i = 0
    table_seen = 0
    summary_tables = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("#"):
            heading = line.strip("# ").strip()
            i += 1
            continue
        if not line.strip().startswith("|"):
            i += 1
            continue
        block = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            block.append(lines[i])
            i += 1
        if len(block) < 2:
            continue
        header = _cells(block[0])
        cols = {key: _find_col(header, names) for key, names in HEADER_KEYS.items()}
        missing = [key for key, idx in cols.items() if idx is None]
        if missing:
            head = "".join(header)
            # 汇总统计表（集|镜数|固定占比…）不是逐镜表：静默跳过，最后统一报缺口，
            # 否则会把「已有统计表但没逐镜表」误报成「逐镜表缺列」。
            if any(word in head for word in ("镜数", "占比")):
                summary_tables += 1
                continue
            if any(k in head for k in ("景别", "焦段", "机位", "运镜")):
                errors.append(f"逐镜表缺列：{'、'.join(missing)}（表头：{block[0].strip()[:60]}）")
            continue
        table_seen += 1
        opt = {key: _find_col(header, names) for key, names in OPTIONAL_KEYS.items()}
        for raw in block[1:]:
            if SEP_RE.match(raw):
                continue
            cells = _cells(raw)
            if not any(cells):
                continue
            def get(key: str) -> str:
                idx = cols.get(key) if key in cols else opt.get(key)
                return cells[idx] if idx is not None and idx < len(cells) else ""
            size = _size(get("景别"))
            focal = _focal(get("焦段"))
            shot_no = get("镜") or f"#{len(shots) + 1}"
            if not size:
                errors.append(f"{heading or '分镜'} {shot_no}：景别「{get('景别')}」不可识别")
            if focal is None:
                errors.append(f"{heading or '分镜'} {shot_no}：焦段「{get('焦段')}」不可识别（须写毫米数）")
            shots.append({
                "segment": get("片段") or heading,
                "shot": shot_no,
                "size": size,
                "focal": focal,
                "angle": _norm(get("机位")),
                "move": get("运镜"),
                "fixed": _is_fixed(get("运镜"), get("固定")),
                "escape": _is_escape(get("固定"), get("运镜"), get("备注")),
                "close": size in CLOSE_SIZES,
                "env": size in ENV_SIZES,
            })
    if not table_seen:
        hint = (f"（已找到 {summary_tables} 张统计汇总表，但汇总表无法反查单镜，"
                f"不能替代逐镜表）") if summary_tables else ""
        errors.append(
            "找不到可校验的逐镜表：需含 景别／焦段／机位／运镜 四列"
            + hint + "，格式见 references/storyboard-selfcheck.md")
    return shots, errors


# ---------------------------------------------------------------- 统计

def stats(shots: list[dict]) -> dict:
    total = len(shots)
    if not total:
        return {}
    fixed_all = [s for s in shots if s["fixed"]]
    fixed_quota = [s for s in fixed_all if not s["escape"]]
    focals = {s["focal"] for s in shots if s["focal"] is not None}
    angles = {s["angle"] for s in shots if s["angle"]}
    # 只统计「侧45°」机位；俯拍45°/仰拍45°不属于侧45，不能混入口径。
    side45 = [s for s in shots if "侧45" in s["angle"] or "侧四十五" in s["angle"]]
    normal = [s for s in shots if not s["fixed"] and not s["env"]]
    return {
        "镜数": total,
        "固定": len(fixed_quota),
        "固定占比": round(len(fixed_quota) * 100 / total, 1),
        "焦段种数": len(focals),
        "机位角度种数": len(angles),
        "侧45占比": round(len(side45) * 100 / total, 1),
        "常规占比": round(len(normal) * 100 / total, 1),
        "固定含例外": len(fixed_all),
        "_focals": sorted(focals),
        "_angles": sorted(angles),
    }


def run_lengths(shots: list[dict]) -> tuple[int, list[str]]:
    """最长连续固定（例外也计入连续）与连三近景位置。"""
    longest = 0
    streak = 0
    prev_seg = None
    close_streak = 0
    close_hits: list[str] = []
    for shot in shots:
        if shot["segment"] != prev_seg:
            streak = 0
            close_streak = 0
            prev_seg = shot["segment"]
        streak = streak + 1 if shot["fixed"] else 0
        longest = max(longest, streak)
        close_streak = close_streak + 1 if shot["close"] else 0
        if close_streak == 3:
            close_hits.append(f"{shot['segment']}→{shot['shot']}")
    return longest, close_hits


# ---------------------------------------------------------------- 声明比对

def parse_declared(text: str) -> tuple[dict, str | None]:
    match = STAT_RE.search(text)
    if not match:
        return {}, None
    raw = match.group(1).strip()
    out: dict[str, float] = {}
    for part in re.split(r"[；;]", raw):
        if "=" not in part and "＝" not in part:
            continue
        key, _, value = re.split(r"([=＝])", part, maxsplit=1)
        key = key.strip()
        num = re.search(r"-?\d+(?:\.\d+)?", value or "")
        if key and num:
            out[key] = float(num.group(0))
    return out, raw


def segment_documents(text: str) -> list[tuple[str, str]]:
    """Return clip-scoped sections so a whole storyboard never compares every clip to one stat row."""
    headings = list(SEGMENT_HEADING_RE.finditer(text))
    if not headings:
        return [("分镜", text)]
    documents: list[tuple[str, str]] = []
    for index, heading in enumerate(headings):
        start = heading.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[start:end]
        shots, _ = parse_shots(block)
        if shots or STAT_RE.search(block):
            title = text[heading.start():text.find("\n", heading.start())].lstrip("# ").strip()
            match = SEGMENT_ID_RE.search(title)
            documents.append((match.group(1) if match else title or "分镜", block))
    return documents or [("分镜", text)]


def _check_one(text: str, label: str, tier: str) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    shots, parse_errors = parse_shots(text)
    errors.extend(parse_errors)
    if not shots:
        return errors, warnings

    computed = stats(shots)
    declared, raw = parse_declared(text)
    if not declared:
        errors.append(
            f"{label} 缺「视感统计：」行，无法交叉校验（格式见 references/storyboard-selfcheck.md，"
            f"可用 --emit 从逐镜表反算）")
    else:
        for key in REQUIRED_STATS:
            if key not in declared:
                errors.append(f"{label} 视感统计缺键「{key}」")
        for key in REQUIRED_STATS:
            if key not in declared or key not in computed:
                continue
            dec, real = declared[key], computed[key]
            if key == "机位角度种数":
                if abs(dec - real) > 1:
                    errors.append(
                        f"{label} {key}：声明 {dec:g}，实算 {real:g}（容差 ±1，超出即统计有误）")
            elif key.endswith("占比"):
                if abs(dec - real) > 1.0:
                    errors.append(f"{label} {key}：声明 {dec:g}%，实算 {real:g}%（容差 ±1pp）")
            elif dec != real:
                errors.append(f"{label} {key}：声明 {dec:g}，实算 {real:g}")

    # ---- 配额（由实算值判定，不采信声明）
    tier2 = tier != "tier1_standard"
    if not tier2:
        warnings.append(f"{label} 第一档：只校验声明一致性，不套小墨配额")
        return errors, warnings

    if computed["固定占比"] > 11.0:
        errors.append(
            f"{label} 固定镜头占比 {computed['固定占比']:g}% 超 10%"
            f"（{computed['固定']}/{computed['镜数']}，例外固定 {computed['固定含例外'] - computed['固定']} 个）")
    longest, close_hits = run_lengths(shots)
    if longest > 1:
        errors.append(f"{label} 出现连续固定镜头 {longest} 个（上限 1，例外固定也计入连续）")
    if close_hits:
        errors.append(f"{label} 景别连三近景：{'、'.join(close_hits)}")
    if computed["焦段种数"] < 4:
        errors.append(f"{label} 焦段只有 {computed['焦段种数']} 种（第二档要求 ≥4）：{computed['_focals']}")
    if computed["机位角度种数"] < 6:
        errors.append(
            f"{label} 机位角度只有 {computed['机位角度种数']} 种（第二档要求 ≥6）：{computed['_angles']}")
    if computed["侧45占比"] <= 0:
        warnings.append(f"{label} 未见侧45°机位，第二档要求侧45°为叙事主力")
    return errors, warnings


def check_text(text: str, label: str = "分镜", tier: str = "tier2_xiaomo63") -> tuple[list, list]:
    """Check each clip independently; retain whole-file behavior for a one-clip document."""
    documents = segment_documents(text)
    if len(documents) == 1:
        return _check_one(text, label, tier)
    errors: list[str] = []
    warnings: list[str] = []
    for clip_label, block in documents:
        clip_errors, clip_warnings = _check_one(block, f"{label} / {clip_label}", tier)
        errors.extend(clip_errors)
        warnings.extend(clip_warnings)
    return errors, warnings


def emit(text: str) -> str:
    output = []
    documents = segment_documents(text)
    for label, block in documents:
        shots, errors = parse_shots(block)
        if not shots:
            output.extend(errors)
            continue
        computed = stats(shots)
        parts = [f"{k}={computed[k]:g}{'%' if k.endswith('占比') else ''}" for k in REQUIRED_STATS]
        prefix = f"{label}：" if len(documents) > 1 and label != "分镜" else ""
        output.append(prefix + "视感统计：" + "；".join(parts))
    return "\n".join(output)


def main() -> int:
    ap = argparse.ArgumentParser(description="分镜视感自查交叉校验")
    ap.add_argument("path", type=Path)
    ap.add_argument("--tier", default="tier2_xiaomo63",
                    choices=["tier1_standard", "tier2_xiaomo63", "tier3_full_xiaomo63"])
    ap.add_argument("--emit", action="store_true", help="只输出统计行，供粘回分镜文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.path.is_file():
        print(f"文件不存在：{args.path}", file=sys.stderr)
        return 2
    text = args.path.read_text(encoding="utf-8")
    if args.emit:
        print(emit(text))
        return 0
    errors, warnings = check_text(text, args.path.name, args.tier)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=1))
    else:
        for w in warnings:
            print(f"  提醒：{w}")
        for e in errors:
            print(f"  错误：{e}")
        print(f"\n视感交叉校验：{'通过' if not errors else '失败'}"
              f"（{len(errors)} 错误 / {len(warnings)} 提醒）")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
