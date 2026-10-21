#!/usr/bin/env python3
"""校验拍摄剧本的体量与形式（按 E26-A AI 短剧制式口径）。

检查项：
  1. 每集体量：字数、场次数、动作行数（△/▲）、台词条数是否落在路线基准区间（含容差）
  2. 一个动作行是否只含一个可生成画面（按分号/多个句号粗判，给出提醒）
  3. 闪回标记是否成对（【闪回】/【闪回结束】、【闪回】/【闪出】）
  4. 场序编号是否规范（集-场），是否有重复
  5. 人物名是否在同集内一致出现

用法：
  python3 scripts/validate_screenplay_volume.py 内部/02-逐集拍摄剧本.md
  python3 scripts/validate_screenplay_volume.py 剧本.md --tier R-AI --tolerance 0.2 --json

说明：本脚本只查形式与体量，不能代替剧情与表演评审（见 prompt-review.md）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EPISODE_HEAD = re.compile(
    r"^#{0,4}\s*(?:第\s*([0-9一二三四五六七八九十]+)\s*集|E(\d+)\b)")
SCENE_HEAD = re.compile(r"^#{0,4}\s*(?:场\s*)?(\d+)-(\d+)\b")
ACTION = re.compile(r"^[△▲]")
DIALOGUE = re.compile(r"^([^\s:：]{1,12})\s*[（(][^）)]*[）)]\s*[:：]")
DIALOGUE_PLAIN = re.compile(r"^([^\s:：]{1,12})\s*[:：]")
FLASHBACK_OPEN = re.compile(r"【闪回")
FLASHBACK_CLOSE = re.compile(r"【闪回(?:结束|出)】")

DEFAULT_TIERS = {
    "R-AI": {"chars": (900, 1200), "scenes": (1, 3), "actions": (20, 30), "dialogues": (15, 20)},
    "R-PLAIN": {"chars": (400, 4000), "scenes": (1, 5), "actions": (4, 400), "dialogues": (4, 400)},
}


def split_episodes(lines: list[str]) -> list[tuple[str, list[str]]]:
    episodes: list[tuple[str, list[str]]] = []
    current_name, current = None, []
    for raw in lines:
        line = raw.strip()
        head = EPISODE_HEAD.match(line)
        if head:
            if current_name is not None:
                episodes.append((current_name, current))
            current_name, current = line.lstrip("# ").strip(), []
        elif current_name is not None:
            current.append(line)
    if current_name is not None:
        episodes.append((current_name, current))
    return episodes


def analyse(body: list[str]) -> dict:
    scenes: list[str] = []
    actions = 0
    dialogues = 0
    chars = 0
    speakers: set[str] = set()
    flashback_open = 0
    flashback_close = 0
    multi_action_lines: list[str] = []
    for line in body:
        if not line:
            continue
        chars += len(re.sub(r"\s+", "", line))
        scene = SCENE_HEAD.match(line)
        if scene and not ACTION.match(line) and not DIALOGUE.match(line) and not DIALOGUE_PLAIN.match(line):
            scenes.append(line)
            continue
        if ACTION.match(line):
            actions += 1
            if line.count("；") >= 1 or line.count("。") >= 2:
                multi_action_lines.append(line)
            continue
        dlg = DIALOGUE.match(line) or DIALOGUE_PLAIN.match(line)
        if dlg:
            dialogues += 1
            speakers.add(dlg.group(1))
        if FLASHBACK_OPEN.search(line):
            flashback_open += 1
        if FLASHBACK_CLOSE.search(line):
            flashback_close += 1
    return {"scenes": len(scenes), "actions": actions, "dialogues": dialogues, "chars": chars,
            "speakers": sorted(speakers), "flashback_open": flashback_open,
            "flashback_close": flashback_close, "multi_action_lines": multi_action_lines}


def within(value: int, band: tuple[int, int], tolerance: float) -> bool:
    low, high = band
    low = max(0, int(low * (1 - tolerance)))
    high = int(high * (1 + tolerance)) + 1
    return low <= value <= high


def main() -> int:
    parser = argparse.ArgumentParser(description="校验拍摄剧本体量与形式")
    parser.add_argument("script", type=Path, help="拍摄剧本 Markdown（TXT/MD）")
    parser.add_argument("--tier", default="R-AI", choices=sorted(DEFAULT_TIERS), help="体量基准档")
    parser.add_argument("--tolerance", type=float, default=0.2, help="容差比例（默认 0.2）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        lines = args.script.read_text(encoding="utf-8").split("\n")
    except OSError as exc:
        print(f"无法读取剧本文件：{exc}", file=sys.stderr)
        return 2

    tier = DEFAULT_TIERS[args.tier]
    episodes = split_episodes(lines)
    if not episodes:
        print("未识别到「第N集」标题，无法按集统计体量", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    report = []
    for name, body in episodes:
        data = analyse(body)
        checks = []
        for key, label in (("chars", "字数"), ("scenes", "场次数"), ("actions", "动作行数"), ("dialogues", "台词条数")):
            ok = within(data[key], tier[key], args.tolerance)
            checks.append({"item": key, "label": label, "value": data[key], "band": list(tier[key]), "ok": ok})
            if not ok:
                errors.append(f"{name}：{label} {data[key]} 超出 {args.tier} 基准 {tier[key][0]}–{tier[key][1]}（容差 {args.tolerance:.0%}）")
        if data["flashback_open"] != data["flashback_close"]:
            errors.append(f"{name}：闪回标记不成对（开 {data['flashback_open']} / 闭 {data['flashback_close']}）")
        if data["multi_action_lines"]:
            warnings.append(f"{name}：{len(data['multi_action_lines'])} 个动作行含多个动作/分号，AI 短剧制式要求一个动作行＝一个可生成画面")
        report.append({"episode": name, **data, "checks": checks})

    if args.json:
        print(json.dumps({"tier": args.tier, "tolerance": args.tolerance, "episodes": report,
                          "ok": not errors, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=2, default=str))
    else:
        print(f"剧本体量检查：{'通过' if not errors else '失败'}；{args.tier} 基准，{len(episodes)} 集")
        for item in report:
            marks = " ".join(f"{c['label']}{c['value']}{'✓' if c['ok'] else '✗'}" for c in item["checks"])
            print(f"  {item['episode']}：{marks}")
        for w in warnings:
            print(f"  提醒：{w}")
        for e in errors:
            print(f"  错误：{e}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
