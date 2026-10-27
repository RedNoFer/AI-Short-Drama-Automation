#!/usr/bin/env python3
"""批次台账与状态机：阶段、草稿、评审、出口门与依赖版本在一处对齐。

为什么有这个脚本（2026-10-25 流程优化）
--------------------------------------------------------------------------
并行执行时最贵的不是写，是**总控反复核对**：这批评了没有、评的是不是同一版、
上游改了以后哪几批作废了。这些答案此前散在对话记录里，每次合并都要重问一遍，
墙钟时间就是这么烧掉的。

本脚本把批次状态收成一份台账（`内部/批次台账.json`），四个状态固定：
`待写` → `待评` → `通过`／`退修`（[多智能体隔离执行规范](../references/multi-agent-execution.md) 定义）。

它替总控盯三件事，而且只盯这三件：

  1. **版本锁**：记录被评草稿与评审版本；阶段4分节报告按本批证据和共享约束锁定，
     其他片段的报告变化不使本批失效；旧平铺报告仍用整文件锁。
  2. **上游失效**：共享母版变化使依赖批次退修；逐镜表变化按本批片段哈希定位，
     只退回受影响批次。
  3. **规范漂移**：manifest 的 policy 版本与当前 policy 不一致，提醒「这批评的是旧规范」，
     但不自动作废——是否重跑由总控按改动范围决定。

用法：
    python3 batch_ledger.py 创作输出/作品名 sync      # 扫 内部/派单/*.manifest.json 建账
    python3 batch_ledger.py 创作输出/作品名 status    # 打印状态与三类问题
    python3 batch_ledger.py 创作输出/作品名 set --batch-id E01-SH01-SH02-1a2b3c4d \
        --state 通过 --draft 内部/派单/E01-SH01-SH02_提示词草稿.md \
        --review 内部/05-提示词评审与整改.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402

SCHEMA = "batch-ledger/1"
LEDGER_NAME = "批次台账.json"
STATES = ("待写", "待评", "退修", "通过")
FINAL_STATES = ("通过",)


def ledger_path(workdir: Path) -> Path:
    return workdir / "内部" / LEDGER_NAME


def load_ledger(workdir: Path) -> dict:
    path = ledger_path(workdir)
    if not path.is_file():
        return {"schema": SCHEMA, "updated": None, "batches": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path.name} schema 应为 {SCHEMA}，实为 {data.get('schema')!r}")
    data.setdefault("batches", [])
    return data


def save_ledger(workdir: Path, data: dict) -> Path:
    path = ledger_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["schema"] = SCHEMA
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def rel(workdir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workdir.resolve()))
    except ValueError:
        return str(path)


def find_manifests(workdir: Path) -> list[Path]:
    return sorted((workdir / "内部" / "派单").glob("*.manifest.json"))


def _scope(entry: dict) -> tuple[str, str, str]:
    return (str(entry.get("stage", "")), str(entry.get("batch", "")), str(entry.get("track", "")))


def _draft_hash(path: Path, entry: dict) -> str:
    """Hash the reviewed artifact at the batch's actual scope.

    Stage 3 reviews cover the segments in a batch, while their draft path often
    points to the merged 04 storyboard. Hashing that whole file reopens every
    Stage 3 batch when one unrelated segment changes. Stage 3 therefore hashes
    only its listed segment blocks; other stages keep the full-file lock.
    """
    if str(entry.get("stage")) != "3":
        return wc.sha256_file(path)
    blocks = {wc.normalize_seg_id(seg): block.strip()
              for seg, block in wc.split_segments(path.read_text(encoding="utf-8"))}
    wanted = [wc.normalize_seg_id(seg) for seg in entry.get("segments") or []]
    missing = [seg for seg in wanted if seg not in blocks]
    if not wanted or missing:
        raise ValueError(f"阶段3批次草稿缺少登记片段：{'、'.join(missing or wanted)}")
    scoped = "\n\n".join(f"### {seg}\n{blocks[seg]}" for seg in wanted)
    return wc.sha256_text(scoped)


def _manifest_dependencies_changed(entry: dict, manifest: dict) -> bool:
    """比较本批真正依赖的输入；逐镜表改了别的段，不作废本批。"""
    old_up = {u.get("label"): u for u in entry.get("upstream") or []}
    new_up = {u.get("label"): u for u in manifest.get("upstream") or []}
    old_segments = entry.get("segment_upstream") or {}
    new_segments = manifest.get("segment_upstream") or {}
    for label in set(old_up) | set(new_up):
        old, new = old_up.get(label), new_up.get(label)
        if old is None or new is None:
            return True
        if label.startswith("片段规划与逐镜表") and old_segments and new_segments:
            if any(old_segments.get(seg) != new_segments.get(seg)
                   for seg in set(old_segments) | set(new_segments)):
                return True
            continue
        if label.startswith("衔接事实") and entry.get("continuity_upstream") and manifest.get("continuity_upstream"):
            if entry["continuity_upstream"] != manifest["continuity_upstream"]:
                return True
            continue
        if (old.get("path"), old.get("sha256"), old.get("present")) != (
                new.get("path"), new.get("sha256"), new.get("present")):
            return True
    return False


def sync(workdir: Path) -> tuple[dict, list[str]]:
    """导入新派单；刷新同一批次的输入快照，并只退回依赖确实变更的批次。"""
    data = load_ledger(workdir)
    notes: list[str] = []
    known = {b["batch_id"]: b for b in data["batches"]}
    known_scopes = {_scope(b): b for b in data["batches"]}
    for path in find_manifests(workdir):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            notes.append(f"{path.name} 不是合法 JSON，跳过：{exc}")
            continue
        bid = manifest.get("batch_id")
        if not bid:
            notes.append(f"{path.name} 缺 batch_id，跳过")
            continue
        existing = known.get(bid) or known_scopes.get(_scope(manifest))
        if existing is not None:
            old_bid = existing.get("batch_id")
            changed = _manifest_dependencies_changed(existing, manifest)
            if changed:
                existing["state"] = "退修" if existing.get("draft") else "待写"
                existing["review"] = None
                existing["review_sha256"] = None
                existing["review_scope"] = None
                existing["reviewed_draft_sha256"] = None
                existing["gate"] = None
                existing["gate_errors"] = None
                notes.append(f"{bid}: 本批依赖输入已变，旧评审与门结果已清除")
            elif (existing.get("state") in FINAL_STATES
                  and not existing.get("reviewed_draft_sha256")
                  and existing.get("draft_sha256") and existing.get("review_sha256")):
                # Safe migration: preserve the ledger's already-recorded approved draft
                # snapshot; diagnose still checks the live draft and review file hashes.
                existing["reviewed_draft_sha256"] = existing["draft_sha256"]
                notes.append(f"{bid}: 补齐历史评审的草稿版本绑定（沿用已登记哈希）")
            existing.update({
                "batch_id": bid,
                "stage": manifest.get("stage"),
                "batch": manifest.get("batch"),
                "segments": manifest.get("segments", []),
                "track": manifest.get("track"),
                "manifest": rel(workdir, path),
                "policy": manifest.get("policy", {}),
                "upstream": manifest.get("upstream", []),
                "segment_upstream": manifest.get("segment_upstream", {}),
                "continuity_upstream": manifest.get("continuity_upstream", {}),
                "card_sha256": manifest.get("card_sha256"),
            })
            if old_bid != bid:
                known.pop(old_bid, None)
                notes.append(f"批次 ID 已迁移：{old_bid} → {bid}")
            known[bid] = existing
            known_scopes[_scope(existing)] = existing
            continue
        entry = {
            "batch_id": bid,
            "stage": manifest.get("stage"),
            "batch": manifest.get("batch"),
            "segments": manifest.get("segments", []),
            "track": manifest.get("track"),
            "state": "待写",
            "manifest": rel(workdir, path),
            "policy": manifest.get("policy", {}),
            "upstream": manifest.get("upstream", []),
            "segment_upstream": manifest.get("segment_upstream", {}),
            "continuity_upstream": manifest.get("continuity_upstream", {}),
            "card_sha256": manifest.get("card_sha256"),
            "draft": None,
            "draft_sha256": None,
            "review": None,
            "review_sha256": None,
            "review_scope": None,
            "reviewed_draft_sha256": None,
            "gate": None,
            "gate_errors": None,
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        data["batches"].append(entry)
        known[bid] = entry
        notes.append(f"登记新批次 {bid}（阶段 {entry['stage']}，{len(entry['segments'])} 片段）")
    return data, notes


def set_state(workdir: Path, batch_id: str, state: str,
              draft: Path | None, review: Path | None,
              gate: str | None) -> tuple[dict, list[str]]:
    data = load_ledger(workdir)
    entry = next((b for b in data["batches"] if b["batch_id"] == batch_id), None)
    if entry is None:
        raise ValueError(f"台账里没有批次「{batch_id}」（先跑 sync）")
    if state not in STATES:
        raise ValueError(f"状态只能是 {'／'.join(STATES)}")
    notes: list[str] = []
    draft_changed = False
    previous_review_sha256 = entry.get("review_sha256")
    previous_scope = entry.get("review_scope")
    if draft:
        if not draft.is_file():
            raise ValueError(f"草稿不存在：{draft}")
        draft_rel = rel(workdir, draft)
        draft_hash = _draft_hash(draft, entry)
        draft_changed = draft_rel != entry.get("draft") or draft_hash != entry.get("draft_sha256")
        if draft_changed:
            entry["review"] = None
            entry["review_sha256"] = None
            entry["review_scope"] = None
            entry["reviewed_draft_sha256"] = None
            entry["gate"] = None
            entry["gate_errors"] = None
        entry["draft"] = draft_rel
        entry["draft_sha256"] = draft_hash
    if review:
        if not review.is_file():
            raise ValueError(f"评审记录不存在：{review}")
        review_rel = rel(workdir, review)
        review_sha256 = wc.sha256_file(review)
        scoped = None
        if str(entry.get("stage")) == "4":
            if state == "通过" and review.name == "05-评审索引.md":
                raise ValueError("--review 必须指向实际评审报告；评审索引只用于整套覆盖汇总")
            try:
                scoped = wc.review_scope_snapshot(review.read_text(encoding="utf-8"), entry.get("segments") or [])
            except ValueError:
                if state == "通过":
                    raise
        if draft_changed and previous_review_sha256 and (
                review_sha256 == previous_review_sha256
                or (previous_scope is not None and scoped == previous_scope)):
            raise ValueError("草稿已变化，但提交的仍是旧评审文件；必须生成并登记本版本的新评审记录")
        entry["review"] = review_rel
        entry["review_sha256"] = review_sha256
        entry["review_scope"] = scoped
        entry["reviewed_draft_sha256"] = entry.get("draft_sha256")
    if gate is not None:
        entry["gate"] = gate
        m = re.search(r"(\d+)\s*错误", gate)
        entry["gate_errors"] = int(m.group(1)) if m else None
    if state == "通过":
        if not entry.get("review_sha256"):
            raise ValueError("标「通过」必须给 --review（评审记录），否则无法证明评过")
        if not entry.get("draft") or not entry.get("draft_sha256"):
            raise ValueError("标「通过」必须给 --draft 并记录被评正文哈希")
        gate_counts = re.findall(r"(?<!\d)(\d+)\s*错误", entry.get("gate") or "")
        if len(gate_counts) != 1 or int(gate_counts[0]) != 0:
            raise ValueError("标「通过」必须提供明确且唯一的「0 错误」门结果；缺失、无法解析或非零均阻断")
        if draft_changed and not review:
            raise ValueError("草稿版本已变化，旧评审已清除；必须同时提交本版本的新评审记录")
        if not review and str(entry.get("stage")) == "4":
            report_path = workdir / entry["review"]
            if report_path.name == "05-评审索引.md":
                raise ValueError("--review 必须指向实际评审报告；评审索引只用于整套覆盖汇总")
            if not report_path.is_file():
                raise ValueError(f"评审记录不存在：{report_path}")
            current_scope = wc.review_scope_snapshot(
                report_path.read_text(encoding="utf-8"), entry.get("segments") or [])
            if entry.get("review_scope") is not None:
                if current_scope != entry["review_scope"]:
                    raise ValueError("本批评审范围已变，须明确登记本版本的新评审记录")
            elif wc.sha256_file(report_path) != entry.get("review_sha256"):
                raise ValueError("旧平铺评审文件已变化，须明确登记新评审记录")
            else:
                entry["review_scope"] = current_scope
    entry["state"] = state
    entry["updated"] = datetime.now().isoformat(timespec="seconds")
    return data, notes


def diagnose(workdir: Path, data: dict) -> tuple[list[str], list[str]]:
    """三件事：哈希对齐、上游失效、规范漂移。"""
    errors: list[str] = []
    warnings: list[str] = []
    snapshot = wc.policy_snapshot()
    for entry in data["batches"]:
        bid = entry.get("batch_id")
        if entry.get("state") in FINAL_STATES:
            draft = entry.get("draft")
            approved_draft_sha256 = entry.get("draft_sha256")
            if not approved_draft_sha256:
                errors.append(f"{bid}: 状态「通过」但没有被评草稿哈希")
            elif draft:
                path = workdir / draft
                if not path.is_file():
                    errors.append(f"{bid}: 草稿文件已不存在（{draft}），通过结论失效")
                else:
                    try:
                        current_draft_hash = _draft_hash(path, entry)
                    except (OSError, UnicodeError, ValueError) as exc:
                        errors.append(f"{bid}: 无法核对被评草稿范围：{exc}")
                    else:
                        if current_draft_hash != approved_draft_sha256:
                            scope_label = "本批分镜片段" if str(entry.get("stage")) == "3" else "草稿"
                            errors.append(f"{bid}: {scope_label}哈希已变（评的是 {approved_draft_sha256[:12]}…，现在是 "
                                          f"{current_draft_hash[:12]}…）——须重评后才能算通过")
            review = entry.get("review")
            review_hash = entry.get("review_sha256")
            if not review or not review_hash:
                errors.append(f"{bid}: 状态「通过」缺评审记录或评审文件哈希")
            else:
                if entry.get("reviewed_draft_sha256") != approved_draft_sha256:
                    errors.append(f"{bid}: 评审记录未绑定当前草稿哈希，旧结论失效")
                review_path = workdir / review
                if not review_path.is_file():
                    errors.append(f"{bid}: 评审文件已不存在（{review}），通过结论失效")
                elif wc.sha256_file(review_path) != review_hash:
                    if entry.get("review_scope") is not None:
                        try:
                            current_scope = wc.review_scope_snapshot(
                                review_path.read_text(encoding="utf-8"), entry.get("segments") or [])
                            if current_scope != entry["review_scope"]:
                                errors.append(f"{bid}: 本批评审范围或共享约束已变（{review}），须定向复验")
                        except ValueError as exc:
                            errors.append(f"{bid}: 本批评审范围无效：{exc}")
                    else:
                        errors.append(f"{bid}: 评审文件哈希已变（{review}），旧平铺报告须重新确认评审")
            gate_counts = re.findall(r"(?<!\d)(\d+)\s*错误", entry.get("gate") or "")
            if len(gate_counts) != 1 or int(gate_counts[0]) != 0:
                errors.append(f"{bid}: 状态「通过」缺少有效的唯一「0 错误」门结果")
        for up in entry.get("upstream") or []:
            if not up.get("present") or not up.get("path"):
                continue
            path = workdir / up["path"]
            if not path.is_file():
                errors.append(f"{bid}: 上游「{up.get('label')}」已不存在（{up['path']}）")
            elif (up.get("label", "").startswith("片段规划与逐镜表")
                  and entry.get("segment_upstream")):
                current = {seg: body for seg, body in wc.split_segments(path.read_text(encoding="utf-8"))}
                changed = [seg for seg, digest in entry["segment_upstream"].items()
                           if seg not in current or wc.sha256_text(current[seg].strip()) != digest]
                if changed:
                    errors.append(f"{bid}: 上游分镜本批片段已变（{'、'.join(changed)}）——只重开本批及其相邻依赖")
            elif up.get("label", "").startswith("衔接事实") and entry.get("continuity_upstream"):
                try:
                    current_scope = wc.continuity_scope_snapshot(path, entry.get("segments") or [])
                    if current_scope != entry["continuity_upstream"]:
                        errors.append(f"{bid}: 本批或相邻接口衔接事实已变，须定向复验")
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    errors.append(f"{bid}: 衔接事实版本无法确认：{exc}")
            elif wc.sha256_file(path) != up.get("sha256"):
                errors.append(f"{bid}: 上游「{up.get('label')}」内容已变——本批次结论失效，须重跑")
        recorded = (entry.get("policy") or {}).get("policy_version")
        if recorded is not None and recorded != snapshot["policy_version"]:
            warnings.append(f"{bid}: 按 policy v{recorded} 生成，当前 v{snapshot['policy_version']}"
                            "——规范已漂移，按改动范围决定是否重跑")
    return errors, warnings


def status_table(data: dict) -> str:
    rows = ["| 批次 | 阶段 | 轨 | 状态 | 片段 | 门 | 被评草稿哈希 | 评审文件哈希 |",
            "|---|---|---|---|---|---|---|---|"]
    for entry in data["batches"]:
        rows.append("| {bid} | {stage} | {track} | {state} | {segs} | {gate} | {d} | {r} |".format(
            bid=entry.get("batch_id", "?"),
            stage=entry.get("stage", "?"),
            track=entry.get("track", "?"),
            state=entry.get("state", "?"),
            segs="、".join(entry.get("segments") or []) or "—",
            gate=(entry.get("gate") or "—") if entry.get("gate") is None
            else f"{entry.get('gate')}（{entry.get('gate_errors') if entry.get('gate_errors') is not None else '?'} 错）",
            d=(entry.get("draft_sha256") or "—")[:12],
            r=(entry.get("review_sha256") or "—")[:12],
        ))
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="批次台账：登记、改状态、看进度与失效")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("action", choices=["sync", "set", "status"], help="sync 建账／set 改状态／status 看状态")
    ap.add_argument("--batch-id", help="批次 ID（set 必填）")
    ap.add_argument("--state", help="待写／待评／退修／通过（set 必填）")
    ap.add_argument("--draft", type=Path, help="草稿路径（相对工作区或绝对路径）")
    ap.add_argument("--review", type=Path, help="评审记录路径")
    ap.add_argument("--gate", help='门结果，如 "0 错误"')
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()
    workdir = args.workdir
    if not (workdir / "内部").is_dir():
        print(f"缺 {workdir}/内部（先完成阶段 0 落盘）", file=sys.stderr)
        return 2
    try:
        if args.action == "sync":
            data, notes = sync(workdir)
            path = save_ledger(workdir, data)
            for n in notes:
                print(n)
            print(f"台账 → {path}（{len(data['batches'])} 批次）")
            return 0
        if args.action == "set":
            if not (args.batch_id and args.state):
                raise ValueError("set 需要 --batch-id 与 --state")
            draft = (workdir / args.draft) if args.draft and not args.draft.is_absolute() else args.draft
            review = (workdir / args.review) if args.review and not args.review.is_absolute() else args.review
            data, notes = set_state(workdir, args.batch_id, args.state, draft, review, args.gate)
            path = save_ledger(workdir, data)
            for n in notes:
                print(n)
            print(f"批次 {args.batch_id} → {args.state}（台账 {path}）")
            return 0
        data = load_ledger(workdir)
        errors, warnings = diagnose(workdir, data)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"ok": not errors, "ledger": data,
                          "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        print(status_table(data))
        print()
        for e in errors:
            print(f"错误：{e}")
        for w in warnings:
            print(f"提醒：{w}")
        total = len(data["batches"])
        done = sum(1 for b in data["batches"] if b.get("state") in FINAL_STATES)
        print(f"\n进度：{done}/{total} 批次通过｜{len(errors)} 错误 / {len(warnings)} 提醒")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
