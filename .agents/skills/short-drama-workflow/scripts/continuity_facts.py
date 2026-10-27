#!/usr/bin/env python3
"""衔接事实 JSON 与交叉检查（改造三）：把「上一段怎么收、下一段怎么接」变成可机检的数据。

为什么有这个脚本（2026-10-25 流程优化）
--------------------------------------------------------------------------
SPACE-01／SYNC-01 两类事故的共同点是：**衔接事实只存在于写作者脑子里**。上一段结尾
人在门口、手里拿着票据，下一段开头人已经在屋里、票据不见了——分镜表和提示词正文
各自看都自洽，跨段才露馅，而那时已经写完一整批。

本脚本把衔接事实外化成一份 JSON（每个片段一条 entry / exit），再做四类机械核对：

  1. 结构：schema 版本、片段 ID 唯一、next 指向真实存在的片段；
  2. 时间轴：JSON 的逐镜起止必须与正文时间轴逐行一致（转录错位当场抓出）；
  3. 参考绑定：entry 里在画内的人物必须在正文【参考】行有绑定（画内即须可锁脸）；
  4. 跨段闭合：上一段 exit 的地点/人物/道具必须能推出下一段 entry，
     凭空出现的人、凭空消失的持物、地点跳变未声明，都判错。

它不判断「这样接好不好看」——那是评审的活。它只保证**接不上这件事不会再靠肉眼发现**。

用法：
    # 1) 从冻结逐镜表派生事实骨架（时间轴与片段 ID 自动填，人物/道具待填）
    python3 continuity_facts.py 创作输出/作品名 --init --batch "E01-SH01~SH03"
    # 2) 填完后与提示词正文交叉核对
    python3 continuity_facts.py 创作输出/作品名 --check --source 内部/派单/E01_草稿.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402

SCHEMA = "continuity-facts/2"
FACTS_NAME = "04c-衔接事实.json"
TODO_VALUES = {"", "todo", "待填", "待定", "-", "—", "none", "null"}
NUM = r"\d+(?:\.\d+)?"
TIME_LINE = re.compile(rf"^\s*({NUM})\s*-\s*({NUM})\s*秒?[，,]", re.M)
REF_LINE = re.compile(r"^【参考】(.+)$", re.M)
ASSET_RE = re.compile(r"\b(CHAR|LOC|PROP)_([A-Za-z0-9]+)\b")


def is_todo(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in TODO_VALUES
    return False


def load_facts(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"缺衔接事实文件：{path}（先跑 --init 派生骨架）")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 顶层必须为对象")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path.name} schema 应为 {SCHEMA}，实为 {data.get('schema')!r}")
    return data


def parse_body_timeline(block: str) -> list[tuple[float, float]]:
    if "【时间轴】" not in block and any(field in block for field in (
            "integrated_multimodal_description", "detailed_description")):
        # H3 uses cut starts rather than the four-section timeline. The segment
        # duration stays in the package binding; do not infer it from dialogue.
        cuts = [int(a) * 60 + float(b) for a, b in re.findall(
            r"\[Shot \d+\]\s*At\s+(\d+):(\d+(?:\.\d+)?)", block)]
        duration = re.search(r"(?:时长[：:]\s*|｜\s*)(\d+(?:\.\d+)?)\s*秒", block)
        if duration:
            return list(zip([0.0] + cuts, cuts + [float(duration[1])] ))
        return []
    m = re.search(r"【时间轴】([\s\S]*?)(?:【收尾】|```|$)", block)
    scope = m.group(1) if m else block
    return [(float(a), float(b)) for a, b in TIME_LINE.findall(scope)]


def parse_body_refs(block: str) -> set[str]:
    m = REF_LINE.search(block)
    scope = m.group(1) if m else block
    return {f"{a}_{b}" for a, b in ASSET_RE.findall(scope)}


def source_axes(source_text: str, source_kind: str) -> tuple[list, dict, dict]:
    """Read actual source order, spans and declared bindings without guessing prose."""
    import scaffold_segment as scaffold
    blocks = wc.split_segments(source_text)
    axes, refs = {}, {}
    for sid, block in blocks:
        if source_kind == "storyboard":
            axes[sid] = [span for row in scaffold.parse_table(block)
                         if (span := scaffold.split_time(row["time"])) is not None]
            meta = scaffold.segment_meta(block)
            refs[sid] = set(meta["char"] + meta["prop"] + meta["scene"])
        else:
            axes[sid] = parse_body_timeline(block)
            refs[sid] = parse_body_refs(block)
    return [sid for sid, _ in blocks], axes, refs


def init_facts(workdir: Path, batch: str | None) -> tuple[dict, Path]:
    internal = workdir / "内部"
    board = None
    for pat in ("04-片段规划与逐镜表.md", "04-*.md"):
        hits = sorted(p for p in internal.glob(pat) if p.is_file() and p.stat().st_size > 0)
        if hits:
            board = hits[0]
            break
    if board is None:
        raise ValueError("缺阶段 3 落盘物「04-片段规划与逐镜表.md」——PROC-05：上游缺失时下游不得开工")
    import scaffold_segment as scaffold  # 复用同一套逐镜表解析，避免两处口径

    blocks = dict(wc.split_segments(board.read_text(encoding="utf-8")))
    want = [wc.normalize_seg_id(x) for x in (wc.parse_batch_ids(batch) if batch else list(blocks))]
    missing = [w for w in want if w not in blocks]
    if missing:
        raise ValueError(f"逐镜表里找不到片段：{'、'.join(missing)}")

    segments = []
    for i, seg_id in enumerate(want):
        rows = scaffold.parse_table(blocks[seg_id])
        spans = [scaffold.split_time(r["time"]) for r in rows]
        shots = [{"no": r["shot"], "start": s[0], "end": s[1]}
                 for r, s in zip(rows, spans) if s]
        meta = scaffold.segment_meta(blocks[seg_id])
        segments.append({
            "id": seg_id,
            "shots": shots,
            "entry": {
                "location": meta["scene"][0] if meta["scene"] else "TODO",
                "time_of_day": "TODO",
                "light": "TODO",
                "characters": [{"code": c, "pos": "TODO", "face": "TODO",
                                "costume": "TODO", "injury": "TODO"} for c in meta["char"]],
                "props": [{"code": p, "state": "TODO"} for p in meta["prop"]],
            },
            "exit": {
                "location": "TODO",
                "time_of_day": "TODO",
                "light": "TODO",
                "characters": [],
                "props": [],
                "leaves": [],
            },
            "next": want[i + 1] if i + 1 < len(want) else None,
            "transition": {"type": "continuous", "reason": "", "evidence": ""},
            "handoff_changes": [],
        })
    data = {
        "schema": SCHEMA,
        "policy": wc.policy_snapshot(),
        "upstream": {"file": board.name, "sha256": wc.sha256_file(board)},
        "segments": segments,
    }
    return data, internal / FACTS_NAME


def check_facts(facts: dict, source_text: str,
                source_kind: str = "prompt") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(facts, dict) or facts.get("schema") != SCHEMA:
        return [f"衔接事实 schema 必须为 {SCHEMA}，旧记录须补齐后重新验收"], []
    segments = facts.get("segments")
    if not isinstance(segments, list) or not segments or not all(isinstance(s, dict) for s in segments):
        return ["衔接事实里没有任何片段"], warnings

    ids = [s.get("id") for s in segments]
    if any(not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9]+-SH\d+", sid) for sid in ids):
        return ["衔接事实片段 ID 必须为规范形式 E01-SH01，不能缺失或为复杂对象"], []
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"片段 ID 重复：{'、'.join(sorted(dupes))}")
    known = set(ids)
    for seg in segments:
        nxt = seg.get("next")
        if nxt is not None and not isinstance(nxt, str):
            errors.append(f"{seg.get('id')}: next 必须为片段 ID 或 null")
        elif nxt and nxt not in known:
            errors.append(f"{seg.get('id')}: next 指向不存在的片段「{nxt}」")

    source_order, axes, bindings = source_axes(source_text, source_kind)
    if not source_order:
        return errors + ["源文件没有可识别片段，不能完成衔接交叉验收"], warnings
    if len(source_order) != len(set(source_order)):
        errors.append("源文件片段 ID 重复，不能完成衔接交叉验收")
    body_norm = dict(wc.split_segments(source_text))
    for seg_id in known:
        if seg_id not in body_norm:
            errors.append(f"{seg_id}: 正文里没有这个片段（事实与正文不同源）")
    for seg_id in body_norm:
        if seg_id not in known:
            errors.append(f"{seg_id}: 正文有该片段，但衔接事实里没有登记")

    for index, sid in enumerate(source_order):
        fact = next((s for s in segments if s["id"] == sid), None)
        if fact is not None:
            expected_next = source_order[index + 1] if index + 1 < len(source_order) else None
            if fact.get("next") != expected_next:
                errors.append(f"{sid}: next 必须指向源文件相邻片段 {expected_next}，不能跳过接口或提前结束")

    for seg in segments:
        for phase in ("entry", "exit"):
            state = seg.get(phase)
            if not isinstance(state, dict):
                errors.append(f"{seg['id']}: 缺少 {phase} 状态对象")
                continue
            for key in ("location", "time_of_day", "light"):
                if not isinstance(state.get(key), str) or is_todo(state.get(key)):
                    errors.append(f"{seg['id']}: {phase}.{key} 缺失或仍是 TODO")
            for group, keys in (("characters", ("code", "pos", "face", "costume", "injury")),
                                ("props", ("code", "state"))):
                rows = state.get(group)
                if not isinstance(rows, list):
                    errors.append(f"{seg['id']}: {phase}.{group} 必须显式登记数组（没有则 []）")
                    continue
                codes = []
                for item in rows:
                    if not isinstance(item, dict):
                        errors.append(f"{seg['id']}: {phase}.{group} 必须为完整对象，不能只有代码")
                        continue
                    for key in keys:
                        if not isinstance(item.get(key), str) or is_todo(item.get(key)):
                            errors.append(f"{seg['id']}: {phase}.{group}.{key} 缺失或仍是 TODO")
                    codes.append(item.get("code"))
                if all(isinstance(c, str) for c in codes) and len(codes) != len(set(codes)):
                    errors.append(f"{seg['id']}: {phase}.{group} 代码重复")
        transition = seg.get("transition", {"type": "continuous"})
        if not isinstance(transition, dict) or transition.get("type") not in {
                "continuous", "cut", "time_jump", "flashback", "dream", "supernatural"}:
            errors.append(f"{seg['id']}: transition 类型无效")
        elif transition["type"] != "continuous" and any(
                not isinstance(transition.get(k), str) or is_todo(transition.get(k))
                for k in ("reason", "evidence")):
            errors.append(f"{seg['id']}: 有意转场须登记 reason 与原文/分镜 evidence")
        changes = seg.get("handoff_changes", [])
        if not isinstance(changes, list):
            errors.append(f"{seg['id']}: handoff_changes 必须为数组")
        else:
            for change in changes:
                if (not isinstance(change, dict) or change.get("kind") not in {
                        "arrival", "departure", "prop", "position", "costume", "injury", "light"}
                        or not isinstance(change.get("code"), str) or is_todo(change.get("code"))
                        or not isinstance(change.get("evidence"), str) or is_todo(change.get("evidence"))):
                    errors.append(f"{seg['id']}: handoff_changes 缺有效 kind/code/evidence")

    # Incomplete or malformed facts never qualify for comparison or a pass.
    if errors:
        return errors, warnings

    for seg in segments:
        seg_id = seg.get("id")
        block = body_norm.get(seg_id)
        if block is None:
            continue
        # 2) 时间轴逐行一致
        try:
            facts_axis = [(float(s["start"]), float(s["end"])) for s in seg.get("shots") or []]
        except (KeyError, TypeError, ValueError):
            facts_axis = []
        body_axis = axes.get(seg_id, [])
        if not facts_axis or not body_axis:
            errors.append(f"{seg_id}: 衔接事实或源文件缺逐镜时间轴，不能跳过同源核对")
        elif facts_axis != body_axis:
            first = next((i for i, (a, b) in enumerate(zip(facts_axis, body_axis)) if a != b),
                         min(len(facts_axis), len(body_axis)))
            errors.append(
                f"{seg_id}: 时间轴与衔接事实不一致（第 {first + 1} 行起）——"
                f"事实 {facts_axis[first] if first < len(facts_axis) else '缺'} vs "
                f"正文 {body_axis[first] if first < len(body_axis) else '缺'}")
        # 3) 画内人物必须绑定
        entry = seg.get("entry") or {}
        refs = bindings.get(seg_id, set())
        for person in entry.get("characters") or []:
            code = person.get("code") if isinstance(person, dict) else person
            if is_todo(code):
                continue
            if code not in refs:
                errors.append(f"{seg_id}: 入口人物 {code} 未在正文【参考】绑定（画内即须可锁脸）")
        for prop in entry.get("props") or []:
            code = prop.get("code") if isinstance(prop, dict) else prop
            if not is_todo(code) and code not in refs:
                errors.append(f"{seg_id}: 入口道具 {code} 未在源文件绑定，持物链可能断")

    # 4) 跨段闭合
    by_id = {s.get("id"): s for s in segments}
    for seg in segments:
        nxt = seg.get("next")
        if not nxt or nxt not in by_id:
            continue
        exit_, entry = seg.get("exit") or {}, by_id[nxt].get("entry") or {}
        following = by_id[nxt]
        transition = following.get("transition") or {}
        intentional_cut = (isinstance(transition, dict) and transition.get("type") in {
            "cut", "time_jump", "flashback", "dream", "supernatural"}
            and all(isinstance(transition.get(k), str) and not is_todo(transition[k])
                    for k in ("reason", "evidence")))
        changes = following.get("handoff_changes") or []
        def declared(kind, code):
            return isinstance(changes, list) and any(isinstance(c, dict)
                and c.get("kind") == kind and c.get("code") == code
                and isinstance(c.get("evidence"), str) and not is_todo(c["evidence"])
                for c in changes)
        loc_a, loc_b = exit_.get("location"), entry.get("location")
        if not intentional_cut and not is_todo(loc_a) and not is_todo(loc_b) and loc_a != loc_b:
            errors.append(f"{seg.get('id')}→{nxt}: 地点跳变 {loc_a} → {loc_b}，"
                          "未在事实里声明转场（同集连续叙事不允许静默换场）")
        tod_a, tod_b = exit_.get("time_of_day"), entry.get("time_of_day")
        if not intentional_cut and not is_todo(tod_a) and not is_todo(tod_b) and tod_a != tod_b:
            errors.append(f"{seg.get('id')}→{nxt}: 时间跳变 {tod_a} → {tod_b}，须有转场依据")
        if not intentional_cut and exit_.get("light") != entry.get("light") and not declared("light", "scene"):
            errors.append(f"{seg['id']}→{nxt}: 光向变化未登记 handoff_changes")

        before = {p.get("code") if isinstance(p, dict) else p
                  for p in exit_.get("characters") or []}
        after = {p.get("code") if isinstance(p, dict) else p
                 for p in entry.get("characters") or []}
        ghost = {c for c in after - before if not is_todo(c) and not declared("arrival", c)}
        if ghost and not intentional_cut:
            errors.append(f"{seg.get('id')}→{nxt}: {'、'.join(sorted(ghost))} 在下一段凭空出现"
                          "（未登记有证据的 arrival）")
        missing = {c for c in before - after if not declared("departure", c)}
        if missing and not intentional_cut:
            errors.append(f"{seg['id']}→{nxt}: {'、'.join(sorted(missing))} 凭空消失，须登记 departure")
        if not intentional_cut:
            previous_people = {p["code"]: p for p in exit_["characters"] if isinstance(p.get("code"), str)}
            for person in entry["characters"]:
                code = person.get("code")
                previous = previous_people.get(code) if isinstance(code, str) else None
                if previous is None:
                    continue
                for key, kind in (("pos", "position"), ("face", "position"),
                                  ("costume", "costume"), ("injury", "injury")):
                    if previous.get(key) != person.get(key) and not declared(kind, code):
                        errors.append(f"{seg['id']}→{nxt}: {code} 的 {key} 改变但无 {kind} 依据")

        carried = {}
        for prop in exit_.get("props") or []:
            if not isinstance(prop, dict):
                continue
            state = str(prop.get("state") or "")
            carried[prop.get("code")] = state
        after_props = {(p.get("code") if isinstance(p, dict) else p)
                       for p in entry.get("props") or []}
        for code, state in carried.items():
            if is_todo(code):
                continue
            if code not in after_props and not intentional_cut and not declared("prop", code):
                errors.append(f"{seg.get('id')}→{nxt}: 道具 {code} 上一段「{state}」，"
                              "下一段入口未登记——持物链可能断，须有放下/离画依据")
        if not intentional_cut:
            for prop in entry["props"]:
                code = prop.get("code")
                if (code not in carried or carried.get(code) != prop.get("state")) and not declared("prop", code):
                    errors.append(f"{seg['id']}→{nxt}: 道具 {code} 新增或状态改变但无 prop 依据")

    if any(is_todo((s.get("entry") or {}).get("location")) for s in segments):
        errors.append("有片段的 entry.location 仍是 TODO：骨架未填完，跨段闭合检查不完整")
    return errors, warnings


def check_project(workdir: Path, source_text: str, source_kind: str) -> tuple[list, list]:
    """Stage gates use the frozen facts; missing or stale sources fail closed."""
    try:
        facts = load_facts(workdir / "内部" / FACTS_NAME)
        errors, warnings = check_facts(facts, source_text, source_kind)
        import scaffold_segment as scaffold
        board = scaffold.pick_storyboard(workdir / "内部")
        if board is None:
            errors.append("衔接事实缺少冻结逐镜表，不能核对上游版本")
        elif facts.get("upstream") != {"file": board.name, "sha256": wc.sha256_file(board)}:
            errors.append("衔接事实的逐镜表版本已过期或未登记；只更新受影响事实后重新验收")
        return errors, warnings
    except (ValueError, OSError, TypeError) as exc:
        return [f"衔接事实检查失败：{exc}"], []


def main() -> int:
    ap = argparse.ArgumentParser(description="衔接事实 JSON：派生骨架或与正文交叉核对")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("--init", action="store_true", help="从冻结逐镜表派生事实骨架")
    ap.add_argument("--check", action="store_true", help="与提示词正文交叉核对")
    ap.add_argument("--batch", help="--init 时的片段范围，如 E01-SH01~SH03")
    ap.add_argument("--source", type=Path, help="--check 时的正文文件（草稿或制作包）")
    ap.add_argument("--facts", type=Path, help="衔接事实路径（缺省 内部/04c-衔接事实.json）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    ap.add_argument("--source-kind", choices=["prompt", "storyboard"], default="prompt")
    args = ap.parse_args()
    if not (args.init or args.check):
        ap.error("必须给 --init 或 --check")
    facts_path = args.facts or (args.workdir / "内部" / FACTS_NAME)
    try:
        if args.init:
            data, _ = init_facts(args.workdir, args.batch)
            path = facts_path
            if path.exists():
                raise ValueError(f"{path} 已存在；不得用待填骨架覆盖已登记事实。分批派生请用 --facts 指定独立路径")
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"衔接事实骨架 → {path}（{len(data['segments'])} 片段，entry/exit 待填）")
            return 0
        facts = load_facts(facts_path)
        if args.source is None:
            raise ValueError("--check 需要 --source 指向正文文件")
        if not args.source.is_file():
            raise ValueError(f"正文文件不存在：{args.source}")
        errors, warnings = check_facts(facts, args.source.read_text(encoding="utf-8"), args.source_kind)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=2))
    else:
        print(f"衔接事实交叉检查｜{facts_path.name} ↔ {args.source.name}")
        for e in errors:
            print(f"错误：{e}")
        for w in warnings:
            print(f"提醒：{w}")
        print(f"结果：{'通过' if not errors else '失败'}（{len(errors)} 错误 / {len(warnings)} 提醒）")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
