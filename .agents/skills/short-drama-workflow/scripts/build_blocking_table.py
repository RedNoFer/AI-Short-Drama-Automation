#!/usr/bin/env python3
"""Build the blocking inheritance table from a station directory (E28 / W18).

Usage:
    python3 build_blocking_table.py <dir> [--out <表.md>] [--scene SCENE_LOC_02]

Reads scene bases and shot overlays, then writes a markdown table with one row
per shot: who moved and why, which side of a character the camera sees, who is
occluded or off screen, and what a seated or handheld prop rests on.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_space_blocking import _chars, _merged_props, _prop_box, _vec3  # noqa: E402

FRONT = "正面可见"
BACK = "只见肩背"
SIDE = "侧面可见"


def _facing_vector(facing):
    """E28 convention: facing 0 points to -Z, +pi/2 to -X."""
    return (-math.sin(facing), -math.cos(facing))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _norm(v):
    return math.hypot(v[0], v[1])


def _unit(v):
    length = _norm(v)
    return (v[0] / length, v[1] / length) if length else (0.0, 0.0)


def _visibility(camera, char, others):
    """Classify the visible side of a character relative to the camera."""
    to_cam = _unit((camera[0] - char["position"][0], camera[2] - char["position"][2]))
    face = _facing_vector(float(char.get("facing", 0.0)))
    d = _dot(to_cam, face)
    if d > 0.35:
        side = FRONT
    elif d < -0.35:
        side = BACK
    else:
        side = SIDE
    occluders = []
    for other in others:
        if other["id"] == char["id"] or not other.get("inFrame"):
            continue
        a = (char["position"][0] - camera[0], char["position"][2] - camera[2])
        b = (other["position"][0] - camera[0], other["position"][2] - camera[2])
        la, lb = _norm(a), _norm(b)
        if lb < 1e-6 or la < 1e-6:
            continue
        if lb >= la:
            continue
        cos = _dot(_unit(a), _unit(b))
        lateral = la * math.sqrt(max(0.0, 1 - cos * cos))
        if cos > 0.93 and lateral < 0.55:
            occluders.append(other["name"])
    return side, occluders


def _support(char, props):
    pose = char.get("posePreset")
    if pose == "sit":
        for prop in props:
            if prop.get("kind") in {"chair", "bench"} and char["id"] in (prop.get("serves") or []):
                return prop["name"]
        for prop in props:
            if prop.get("kind") in {"chair", "bench"}:
                return prop["name"]
    support_id = char.get("supportSurfaceId")
    if support_id:
        surface = next((p for p in props if p.get("id") == support_id
                        and p.get("walkableSurface") is True), None)
        if surface:
            return f"站在{surface['name']}顶面"
    touching = char.get("touching")
    if isinstance(touching, list) and touching:
        names = [p["name"] for p in props if p.get("id") in touching]
        if names:
            return "手触：" + "、".join(names)
    return "地面"


def _shot_order(path: Path):
    """Sort overlays by episode, segment, then shot number (numeric order)."""
    match = re.match(r"^E(\d+)_SH(\d+)_S(\d+)$", path.stem)
    if not match:
        return (10**9, 10**9, 10**9, path.name)
    return tuple(int(part) for part in match.groups()) + (path.name,)


def build(directory, scene_filter=None):
    bases, overlays = {}, []
    for path in sorted(directory.rglob("*.json")):
        if path.name.startswith("_"):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if path.name.startswith("SCENE_"):
            bases[path.stem] = doc
        elif path.name.startswith("E"):
            overlays.append((path, doc))
    overlays.sort(key=lambda item: _shot_order(item[0]))

    rows = []
    previous = None
    for path, doc in overlays:
        base = bases.get(doc.get("base"))
        props = _merged_props(doc, base)
        chars = _chars(doc)
        camera = _vec3((doc.get("camera") or {}).get("position"))
        lines = []
        for char in chars:
            if not char.get("inFrame"):
                continue
            position = _vec3(char.get("position"))
            if position is None or camera is None:
                continue
            side, occluders = _visibility(camera, char, chars)
            support = _support(char, props)
            bits = [f"{char['name']}（{side}）"]
            if occluders:
                bits.append("被" + "、".join(occluders) + "部分遮挡")
            bits.append(f"承托：{support}")
            lines.append("；".join(bits))
        offscreen = [c["name"] for c in chars if not c.get("inFrame")]
        move = "—"
        if previous and doc.get("base") == previous.get("base"):
            prev_chars = {c["id"]: c for c in _chars(previous)}
            moved = []
            for char in chars:
                before = prev_chars.get(char["id"])
                if not before:
                    continue
                a, b = _vec3(before.get("position")), _vec3(char.get("position"))
                if a and b and math.dist(a, b) > 0.01:
                    declared = bool(char.get("movementPath") or before.get("movementPath"))
                    moved.append(f"{char['name']}（{'已声明移动' if declared else '未声明移动'}）")
            move = "；".join(moved) if moved else "无"
        rows.append({
            "shot": doc.get("shot", path.stem),
            "timecode": doc.get("timecode", ""),
            "camera": (doc.get("camera") or {}).get("note", ""),
            "move": move,
            "visible": "；".join(lines) if lines else "无人入画",
            "offscreen": "、".join(offscreen) if offscreen else "无",
        })
        previous = doc
    return rows


def render(rows):
    out = ["# 站位继承表（机检生成）", "",
           "每行一镜：站位变化及来源、机位、可见面与遮挡、承托、画外人物。",
           "「未声明移动」即为 SPACE-01 阻断项，须补 movementPath 或改回上一镜状态。", "",
           "| 镜头 | 时间码 | 机位 | 站位变化 | 画面内可见面与承托 | 画外 |",
           "|---|---|---|---|---|---|"]
    for row in rows:
        out.append(f"| {row['shot']} | {row['timecode']} | {row['camera']} | {row['move']} "
                   f"| {row['visible']} | {row['offscreen']} |")
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="站位继承表生成器")
    parser.add_argument("directory")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    directory = Path(args.directory).expanduser()
    rows = build(directory)
    text = render(rows)
    if args.out:
        Path(args.out).expanduser().write_text(text, encoding="utf-8")
        print(f"站位继承表 → {args.out}（{len(rows)} 镜）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
