#!/usr/bin/env python3
"""Check SCENE_JSON scene bases and shot overlays for blocking consistency (E28 / W18).

Usage:
    python3 validate_space_blocking.py <dir> [--min-gap 0.35] [--strict] [--json]
    python3 validate_space_blocking.py <file.json> [...] [--min-gap 0.35]

Directory mode picks up ``SCENE_*.json`` as scene bases and ``E*_SH*_S*.json`` as
shot overlays; an overlay links to its base through the ``base`` field.

Six mechanical checks (see references/failure-cases.md SPACE-01 item 7):
    1. facing matches the character's facing target
    2. ground contact per posePreset (standing / seated / lying / kneeling)
    3. character-to-solid clearance >= min-gap
    4. movementPath does not cross walls or major props
    5. seated and held props have a support
    6. blocking carries over between consecutive shots unless a move is declared

Only geometry is checked here. Whether a camera placement tells a story is an
agent review job, and no image or video is ever produced by this script.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Pose families from E28 (26站位图+skill/站位Skill/hongmiao-director/SKILL.md).
STANDING = {"stand", "t-pose", "walk", "run", "hands-on-hips", "lean", "bow",
            "think", "fight", "kick", "throw", "push", "wave", "reach",
            "cross-arms", "phone"}
SEATED = {"sit"}
LYING = {"lie"}
CROUCHED = {"crouch", "kneel-one", "kneel-two"}
KNOWN_POSES = STANDING | SEATED | LYING | CROUCHED

SEAT_KINDS = {"chair", "bench"}
SOLID_KINDS = {"table", "chair", "bench", "cup", "tree", "lamp", "device", "box"}
WALL_LIKE = {"wall", "window", "vehicle", "bed", "sofa"}
PATH_BLOCKING_KINDS = {"table", "tree", "lamp", "device", "box", "chair", "bench"}
PATH_BLOCKING_SEMANTICS = {"wall", "vehicle", "bed", "sofa"}

EPS = 1e-6


def _vec3(value):
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _facing_to_target(position, target):
    """E28 convention: facing = atan2(-(tx-x), -(tz-z)); 0 points to -Z."""
    return math.atan2(-(target[0] - position[0]), -(target[2] - position[2]))


def _angle_delta(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def _prop_box(prop):
    """Return (cx, cz, half_x, half_z, height) for a prop, or None."""
    position = _vec3(prop.get("position"))
    size = _vec3(prop.get("size"))
    if position is None or size is None:
        return None
    return (position[0], position[2], abs(size[0]) / 2.0, abs(size[2]) / 2.0, abs(size[1]))


def _distance_to_box(position, box):
    """Horizontal distance from a point to an axis-aligned footprint."""
    cx, cz, hx, hz, _ = box
    dx = max(abs(position[0] - cx) - hx, 0.0)
    dz = max(abs(position[2] - cz) - hz, 0.0)
    return math.hypot(dx, dz)


def _inside_box(position, box, pad=0.0):
    cx, cz, hx, hz, _ = box
    return (abs(position[0] - cx) <= hx + pad
            and abs(position[2] - cz) <= hz + pad)


def _surface_top(prop):
    """Return the top elevation for an explicitly walkable box surface."""
    if prop.get("walkableSurface") is not True or prop.get("kind") != "box":
        return None
    position = _vec3(prop.get("position"))
    size = _vec3(prop.get("size"))
    if position is None or size is None:
        return None
    return position[1] + abs(size[1]) / 2.0


def _camera_in_prop(cam_pos, prop, box):
    """True when the camera sits inside the prop volume (footprint plus height)."""
    cx, cz, hx, hz, height = box
    if not (abs(cam_pos[0] - cx) <= hx and abs(cam_pos[2] - cz) <= hz):
        return False
    base = float(prop.get("position", [0, 0, 0])[1] or 0)
    return base - 1e-6 <= cam_pos[1] <= base + height + 1e-6


def _semantic(prop):
    value = prop.get("semanticType")
    if value:
        return value
    if isinstance(prop.get("box"), dict):
        return prop["box"].get("semanticType")
    return None


def _chars(doc):
    out = []
    for item in doc.get("characters") or []:
        if isinstance(item, dict):
            out.append(item)
    return out


def _props(doc):
    out = []
    for item in doc.get("props") or []:
        if isinstance(item, dict):
            out.append(item)
    return out


def _merged_props(doc, base):
    """Overlay props are deltas: merge field by field onto the scene base."""
    merged = {}
    for prop in _props(base) if base else []:
        merged[prop.get("id")] = dict(prop)
    for prop in _props(doc):
        pid = prop.get("id")
        if pid is None:
            continue
        merged.setdefault(pid, {})
        merged[pid].update(prop)
    return list(merged.values())


def _is_overhead(prop) -> bool:
    """头顶结构（车顶/顶棚/天花板）：y≥1.5m 且厚度≤0.35m。

    人物进出车厢的动线必然从车顶的正投影下方穿过，这不是「穿过实体」；
    地面行走只需避开有厚度的地面物（车身侧板、座椅、护栏、引擎盖）。
    """
    pos = _vec3(prop.get("position")) or [0.0, 0.0, 0.0]
    size = _vec3(prop.get("size")) or [0.0, 0.0, 0.0]
    h = abs(size[1])
    # 高顶棚：y≥1.5 且厚度≤0.35；车内顶棚/行李架：y≥1.25 且厚度≤0.10
    # （人在舱内是坐/俯身通过，顶棚在头顶之上，不是「穿过实体」）
    return (pos[1] >= 1.5 and h <= 0.35) or (pos[1] >= 1.25 and h <= 0.10)


def _exempt_pair(char, prop):
    """Props a character is allowed to touch: own seat, held item, declared contact."""
    cid = char.get("id")
    if prop.get("seatFor") == cid:
        return True
    if prop.get("heldBy") == cid:
        return True
    if char.get("supportSurfaceId") == prop.get("id"):
        return True
    ignored = prop.get("ignoredBy")
    if isinstance(ignored, list) and cid in ignored:
        return True
    touching = char.get("touching")
    if isinstance(touching, list) and prop.get("id") in touching:
        return True
    serves = prop.get("serves")
    if isinstance(serves, list) and cid in serves:
        return True
    return False


def check_base(doc, label, errors, warnings):
    """Structural check for a scene base."""
    for key in ("scene", "characters", "props", "camera", "lighting", "continuity"):
        if key not in doc:
            errors.append(f"{label}: 缺少顶层字段 {key}")
    for char in _chars(doc):
        cid = char.get("id")
        if not cid:
            errors.append(f"{label}: characters 中存在缺少 id 的条目")
            continue
        if _vec3(char.get("position")) is None:
            errors.append(f"{label}: 角色 {cid} 缺少三维 position")
        pose = char.get("posePreset")
        if pose and pose not in KNOWN_POSES:
            errors.append(f"{label}: 角色 {cid} 使用未知 posePreset「{pose}」")
        weapon = char.get("weapon")
        if weapon and weapon in {"sword", "staff", "pistol"}:
            errors.append(f"{label}: 角色 {cid} 使用旧武器 ID「{weapon}」")
    for prop in _props(doc):
        pid = prop.get("id")
        if not pid:
            errors.append(f"{label}: props 中存在缺少 id 的条目")
            continue
        if prop.get("kind") and prop["kind"] not in SOLID_KINDS | WALL_LIKE | {"door"}:
            warnings.append(f"{label}: 道具 {pid} 的 kind「{prop['kind']}」不在 schema 列表内")
        if prop.get("position") is not None and _vec3(prop.get("position")) is None:
            errors.append(f"{label}: 道具 {pid} 的 position 不是三维数值")
        if prop.get("size") is not None and _vec3(prop.get("size")) is None:
            errors.append(f"{label}: 道具 {pid} 的 size 不是三维数值")


def check_geometry(doc, label, base, errors, warnings, min_gap):
    """Checks 1-5 for one scene or overlay document."""
    chars = _chars(doc)
    props = _merged_props(doc, base)
    base_props = props
    if base:
        known = {c.get("id") for c in _chars(base)}
        for char in chars:
            if char.get("id") not in known:
                errors.append(f"{label}: 角色 {char.get('id')} 不在基底场景中，ID 必须稳定")
    prop_boxes = []
    for prop in props:
        box = _prop_box(prop)
        if box:
            prop_boxes.append((prop, box))

    for char in chars:
        cid = char.get("id")
        position = _vec3(char.get("position"))
        if position is None:
            continue
        pose = char.get("posePreset") or "stand"

        # 1. facing consistency
        target = _vec3(char.get("facingTarget") or char.get("lookAt"))
        if target is not None and "facing" in char:
            try:
                expected = _facing_to_target(position, target)
                actual = float(char["facing"])
                if _angle_delta(expected, actual) > 0.05:
                    errors.append(
                        f"{label}: 角色 {cid} facing={actual:.4f} 与目标点计算值 "
                        f"{expected:.4f} 不符（偏差 {_angle_delta(expected, actual):.4f} rad）")
            except (TypeError, ValueError):
                errors.append(f"{label}: 角色 {cid} 的 facing 不是数值")

        # 2. ground contact: default floor is y=0; elevated walkable fixtures
        # must be named explicitly and match both the box top and footprint.
        if pose in STANDING:
            support_id = char.get("supportSurfaceId")
            if support_id is None:
                if abs(position[1]) > 0.02:
                    errors.append(
                        f"{label}: 角色 {cid} posePreset={pose} 但 y={position[1]:.2f} 未接地（默认地面为 y=0；抬高表面需声明 supportSurfaceId）")
            else:
                support = next((p for p in props if p.get("id") == support_id), None)
                support_box = _prop_box(support) if support else None
                top = _surface_top(support) if support else None
                if support is None or support_box is None or top is None:
                    errors.append(
                        f"{label}: 角色 {cid} 的 supportSurfaceId「{support_id}」不是有效 walkableSurface 箱体")
                elif not _inside_box(position, support_box, pad=0.02):
                    errors.append(
                        f"{label}: 角色 {cid} 的 position 不在支撑面 {support_id} 的水平范围内")
                elif abs(position[1] - top) > 0.02:
                    errors.append(
                        f"{label}: 角色 {cid} 的 y={position[1]:.2f} 未落在支撑面 {support_id} 顶面 y={top:.2f}")
        elif pose in LYING and position[1] > 0.35:
            errors.append(f"{label}: 角色 {cid} posePreset=lie 但 y={position[1]:.2f} 离地过高")
        elif pose in CROUCHED and position[1] > 0.75:
            errors.append(f"{label}: 角色 {cid} posePreset={pose} 但 y={position[1]:.2f} 超过蹲跪高度")

        # 3. clearance to solids
        for prop, box in prop_boxes:
            pid = prop.get("id")
            semantic = _semantic(prop)
            if semantic in WALL_LIKE and prop.get("kind") != "box":
                continue
            if _exempt_pair(char, prop):
                continue
            if prop.get("heldBy"):
                # 手持道具随持有人移动，不是固定障碍；只有持有人本身才是障碍
                continue
            if _is_overhead(prop):
                # 头顶灯具/顶棚只与人物高度相交时才构成碰撞；水平投影重叠不算脚下净距冲突。
                continue
            if pose == "sit" and prop.get("kind") in SEAT_KINDS:
                continue
            distance = _distance_to_box(position, box)
            if distance < min_gap - EPS:
                warnings.append(
                    f"{label}: 角色 {cid} 与道具 {pid} 间距 {distance:.2f}m < {min_gap:.2f}m")

        # 5. support for seated characters and held props
        if pose == "sit":
            seats = [p for p, _ in prop_boxes
                     if p.get("kind") in SEAT_KINDS and not _distance_to_box(position, _prop_box(p)) > 1.2]
            if not seats:
                errors.append(
                    f"{label}: 角色 {cid} posePreset=sit 但 1.2m 内没有 chair/bench 承托面")
            else:
                seat = _prop_box(seats[0])
                if seat and abs(position[1] - seat[4]) > 0.15:
                    warnings.append(
                        f"{label}: 角色 {cid} 坐姿 y={position[1]:.2f} 与座面高度 {seat[4]:.2f} 不一致")

        path = char.get("movementPath")
        if path:
            points = [_vec3(p) for p in path]
            points = [p for p in points if p is not None]
            if len(points) < 2:
                errors.append(f"{label}: 角色 {cid} 的 movementPath 少于两个有效点")
            else:
                for prop, box in prop_boxes:
                    pid = prop.get("id")
                    semantic = _semantic(prop)
                    blocking = (prop.get("kind") in PATH_BLOCKING_KINDS
                                or semantic in PATH_BLOCKING_SEMANTICS)
                    if not blocking:
                        continue
                    if _is_overhead(prop) or prop.get("heldBy"):
                        continue
                    if _exempt_pair(char, prop):
                        continue
                    inside_prop = semantic in {"vehicle"} or prop.get("kind") == "vehicle"
                    for start, end in zip(points, points[1:]):
                        if inside_prop and (_in_footprint(start, box) or _in_footprint(end, box)):
                            # 车体：上下车是经车门的合法动作，端点落在舱内不算穿越
                            continue
                        if _segment_hits_box(start, end, box):
                            errors.append(
                                f"{label}: 角色 {cid} 的 movementPath 穿过道具 {pid}")
                            break

    # 5b. held props need a real holder
    known_chars = {c.get("id") for c in chars}
    for prop in props:
        holder = prop.get("heldBy")
        if holder and holder not in known_chars:
            errors.append(f"{label}: 道具 {prop.get('id')} 的 heldBy「{holder}」不在本镜角色中")
        resting = prop.get("restingOn")
        if resting:
            ids = {p.get("id") for p in props}
            if resting not in ids:
                errors.append(f"{label}: 道具 {prop.get('id')} 的 restingOn「{resting}」不存在")

    # camera sanity
    camera = doc.get("camera") or {}
    cam_pos = _vec3(camera.get("position"))
    if cam_pos is None:
        errors.append(f"{label}: camera 缺少三维 position")
    else:
        if cam_pos[1] <= 0:
            errors.append(f"{label}: camera y={cam_pos[1]:.2f} 不高于地面")
        for prop, box in prop_boxes:
            if _camera_in_prop(cam_pos, prop, box):
                errors.append(f"{label}: camera 位于道具 {prop.get('id')} 内部")


def _in_footprint(point, box) -> bool:
    """点是否落在道具的水平投影内（含 0.05m 容差）。"""
    cx, cz, hx, hz, _ = box
    return abs(point[0] - cx) <= hx + 0.05 and abs(point[2] - cz) <= hz + 0.05


def _segment_hits_box(start, end, box, samples=24):
    cx, cz, hx, hz, _ = box
    for step in range(samples + 1):
        t = step / samples
        x = start[0] + (end[0] - start[0]) * t
        z = start[2] + (end[2] - start[2]) * t
        if abs(x - cx) <= hx and abs(z - cz) <= hz:
            return True
    return False


def check_continuity(overlays, label_of, errors, warnings):
    """Check 6: blocking carries over between consecutive shots of one scene."""
    by_scene = {}
    for path, doc in overlays:
        base_id = doc.get("base") or ""
        by_scene.setdefault(base_id, []).append((path, doc))
    for base_id, items in by_scene.items():
        items.sort(key=lambda item: item[0].name)
        for (prev_path, prev), (cur_path, cur) in zip(items, items[1:]):
            prev_chars = {c.get("id"): c for c in _chars(prev)}
            cur_chars = {c.get("id"): c for c in _chars(cur)}
            for cid, prev_char in prev_chars.items():
                cur_char = cur_chars.get(cid)
                if cur_char is None:
                    if not prev_char.get("leftScene"):
                        warnings.append(
                            f"{label_of(cur_path)}: 角色 {cid} 在上一镜存在但本镜消失，且无离席说明")
                    continue
                a = _vec3(prev_char.get("position"))
                b = _vec3(cur_char.get("position"))
                if a is None or b is None:
                    continue
                moved = math.dist(a, b) > 0.01
                if not moved:
                    continue
                declared = (cur_char.get("movementPath") or prev_char.get("movementPath")
                            or cur_char.get("moved") or prev_char.get("moved"))
                if not declared:
                    errors.append(
                        f"{label_of(cur_path)}: 角色 {cid} 站位从 {label_of(prev_path)} "
                        f"变更到本镜，但未声明 movementPath")


def run(paths, min_gap=0.35, strict=False):
    errors, warnings = [], []
    docs = []
    for path in paths:
        try:
            docs.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: 无法读取 JSON（{exc}）")
    bases = {}
    overlays = []
    for path, doc in docs:
        if path.name.startswith("SCENE_"):
            bases[path.stem] = (path, doc)
        else:
            overlays.append((path, doc))

    for path, doc in docs:
        label = path.name
        base = None
        base_id = doc.get("base")
        if base_id:
            base = bases.get(base_id, (None, None))[1]
            if base is None:
                errors.append(f"{label}: 引用了不存在的基础场景「{base_id}」")
        if path.name.startswith("SCENE_"):
            check_base(doc, label, errors, warnings)
        check_geometry(doc, label, base, errors, warnings, min_gap)

    check_continuity(overlays, lambda p: p.name, errors, warnings)

    if strict:
        errors.extend(warnings)
        warnings = []
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="SCENE_JSON 站位一致性机检")
    parser.add_argument("paths", nargs="+", help="站位目录或 JSON 文件")
    parser.add_argument("--min-gap", type=float, default=0.35, help="人与实体道具最小间隙（米）")
    parser.add_argument("--strict", action="store_true", help="把警告升级为错误")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args(argv)

    files = []
    for raw in args.paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.json")
                                if p.name.startswith("SCENE_") or p.name.startswith("E")))
        else:
            files.append(path)

    errors, warnings = run(files, min_gap=args.min_gap, strict=args.strict)
    if args.json:
        print(json.dumps({"files": len(files), "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=2))
    else:
        for item in errors:
            print(f"ERROR  {item}")
        for item in warnings:
            print(f"WARN   {item}")
        print(f"站位机检：{len(files)} 个文件，{len(errors)} 错误 / {len(warnings)} 警告")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
