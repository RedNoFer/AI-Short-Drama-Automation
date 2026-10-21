#!/usr/bin/env python3
"""Audit a Wan3.0 compact package for the WAN30-01 anti-patterns.

This is a *专项审计* companion to validate_compact_package.py --model wan30.
It does not replace the importer/format validator; it reports prompt-level risks
that were confirmed by the 2026-10-20 E01-SH01/SH03 sample:

- camera clause buried at the end of a row
- "极缓慢" without measurable movement
- still-life / empty beats that run too long
- "并肩 / 一字排开 / 并排站 / 排成一排"
- missing "不看镜头"
- dialogue shots longer than 6 seconds
- warm-light words in a cold-gray project
- note/road-sign close-ups that invite gibberish text
- public-spec bloat

Usage:
    python3 audit_wan30_antipatterns.py package.md
    python3 audit_wan30_antipatterns.py package.md --json
    python3 audit_wan30_antipatterns.py package.md --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEGMENT = re.compile(r"^### 片段 ([A-Za-z][A-Za-z0-9_-]*)｜(\d+)秒｜(.+)$")
EPISODE = re.compile(r"^## 剧集 ([A-Za-z][A-Za-z0-9_-]*)｜(.+)$")
PROMPT = re.compile(r"#### 视频提示词\n\n```text\n([\s\S]*?)\n```")
ROW = re.compile(r"^(\d+(?:\.5)?)-(\d+(?:\.5)?)秒[，,](.*)$")
SHOT = re.compile(r"(大远景|远景|全景|中近景|中景|近景|大特写|特写|微距)")
CAMERA_PREFIX = re.compile(r"^(?:硬切[，,。]\s*)?镜头[：:]")

CHARS = ("阿泽", "苏晚", "老杨", "许棠", "小林", "黑衣人")
GROUPS = ("五人", "四人", "三人", "两人", "众人", "大家", "他们", "她们")
BODY = (
    "手指", "指腹", "指尖", "指节", "手腕", "掌心", "手背", "双手",
    "左手", "右手", "手臂", "肩膀", "肩线", "肩头", "后背", "脊背",
    "背影", "脚步", "脚下", "脚尖", "脚底", "脚踝", "膝盖", "呼吸",
    "喉结", "下颌", "睫毛", "目光", "视线", "胸口", "额头", "脸",
    "眼睛", "眼神", "眼底", "嘴角", "嘴唇", "脖子", "身体",
)
PROPS = (
    "包裹", "古图", "字条", "纸条", "手机", "银纹", "图面", "纸面",
    "手绳", "相机",
)
ACTION = re.compile(
    r"(走|跑|蹲|起身|站起|抬头|低头|转身|回头|伸手|抬手|收|放|推|拉|递|接|"
    r"握|攥|翻|擦|按|扶|踩|跨|扑|躲|冲|停|弯腰|直起|侧身|点头|摇头|呼吸|"
    r"吞咽|眨眼|皱眉|抿嘴|咬|抓|提|扛|抱|背|穿|脱|打开|合上|掀|压|抹|蹭|"
    r"拍|敲|指|扫|盯|看|望|掏|塞|拉上|解开|系|甩|绕|踢|靠|坐|躺|趴|钻|"
    r"挤|退|迈|踏|跺|蹲下|俯身|探|缩|转|扭|挣|扶住|撑|搭|勾|划|写|画|"
    r"折|撕|卷|铺|摊|挂|摘|戴|换|洗|点|亮|灭)"
)
TEXT_PROP = re.compile(r"(字条|纸条|路牌|车牌|纸面|图面)")
CLOSE_UP = re.compile(r"(大特写|特写|微距)")
TEXT_WORD = re.compile(r"(墨|字|笔画|可读|笔锋|起笔|书写)")
POSITIVE_GAZE = re.compile(r"(?<!不)看镜头|(?<!不)对镜头")
FIVE_GROUP = re.compile(r"五人(全景|围拢|站|并肩|立|俯身|同框)|五个人|五个人的")
FACE_SHOT = re.compile(r"(大特写|特写|近景|中近景|看镜头|口型对白|正面(?:站|面向|拍))")
REFLECTION = re.compile(r"倒影|复刻|分身|另一个自己|两个阿泽|两个苏晚")
QUOTE = re.compile(r'"[^"]*"|“[^”]*”')
SHADOW = re.compile(r"(影子|倒影|树影|山影|光斑|车影)$")
GROUP = re.compile(r"(五人|众人|四人|三人|大家|他们|她们|队伍|人群|一排|并排)")
STANCE = re.compile(r"(站|立|走|行|排|队列|队形|面向|朝|看|停|等|聚|挤)")


def blocking_hits(text: str, terms: list[str]) -> list[tuple[str, str]]:
    """Return only physical group-lineup hits.

    Avoid false positives confirmed during the WAN30-01 review:
    - dialogue metaphors such as "同心并肩" are stripped as quotes;
    - two people walking side by side ("阿泽与老杨并肩在前") is allowed;
    - shadows lining up ("影子排成一排") is not a character lineup.
    """
    clean = QUOTE.sub("", text)
    hits: list[tuple[str, str]] = []
    reported: set[str] = set()
    for term in terms:
        if term in reported:
            continue
        for m in re.finditer(re.escape(term), clean):
            ctx = clean[max(0, m.start() - 45): m.end() + 45]
            if term == "并肩":
                if not GROUP.search(ctx) or not STANCE.search(ctx):
                    continue
            else:
                before = clean[max(0, m.start() - 8): m.start()]
                if SHADOW.search(before):
                    continue
                if not GROUP.search(ctx):
                    continue
            hits.append((term, ctx))
            reported.add(term)
            break
    return hits


def split_prompt(prompt: str) -> tuple[str, str, str]:
    pub = ""
    timeline = ""
    tail = ""
    if "【公共总规范】" in prompt:
        pub = prompt.split("【公共总规范】", 1)[1].split("【时间轴】", 1)[0]
    if "【时间轴】" in prompt:
        timeline = prompt.split("【时间轴】", 1)[1].split("【收尾】", 1)[0]
    if "【收尾】" in prompt:
        tail = prompt.split("【收尾】", 1)[1]
    return pub, timeline, tail


def parse_segments(text: str):
    current_episode = "?"
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        em = EPISODE.match(lines[i])
        if em:
            current_episode = em.group(1)
            i += 1
            continue
        sm = SEGMENT.match(lines[i])
        if not sm:
            i += 1
            continue
        shot_id, duration, title = sm.group(1), int(sm.group(2)), sm.group(3)
        # Find the video prompt fenced block until the next segment/episode.
        j = i + 1
        chunk = []
        while j < len(lines) and not SEGMENT.match(lines[j]) and not EPISODE.match(lines[j]):
            chunk.append(lines[j])
            j += 1
        block = "\n".join(chunk)
        pm = PROMPT.search(block)
        if pm:
            yield {
                "episode": current_episode,
                "shot": shot_id,
                "duration": duration,
                "title": title,
                "prompt": pm.group(1).strip(),
            }
        i = j


def audit(package: Path, policy_path: Path | None) -> dict:
    text = package.read_text(encoding="utf-8")
    policy = {}
    if policy_path and policy_path.exists():
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    cfg = (
        policy.get("model_profiles", {}).get("wan30", {}).get("anti_patterns", {})
        or {}
    )
    camera_max = float(cfg.get("camera_clause_max_pos_ratio", 0.30))
    still_max = float(cfg.get("still_shot_max_sec", 2.0))
    empty_max = float(cfg.get("empty_shot_max_sec", 2.5))
    dialogue_max = float(cfg.get("max_dialogue_shot_sec", 6.0))
    pub_max = float(cfg.get("public_spec_max_ratio", 0.20))
    max_extreme = int(cfg.get("max_extreme_slow_terms", 0))
    min_action_nodes = int(cfg.get("min_action_nodes_per_beat", 2))
    max_named_faces = int(cfg.get("max_named_faces_per_shot", 3))
    max_five_sec = float(cfg.get("max_five_person_shot_sec", 2.0))
    forbid_five_dialogue = bool(cfg.get("forbid_five_person_dialogue", True))
    reflection_tag = bool(cfg.get("reflection_requires_fantasy_tag", True))
    blocking_terms = cfg.get(
        "forbidden_blocking_terms", ["并肩", "一字排开", "并排站", "排成一排"]
    )
    warm_terms = cfg.get(
        "warm_light_terms", ["清晨低角度", "金色", "暖金", "日出", "暖色逆光"]
    )

    segments = list(parse_segments(text))
    rows_total = 0
    issues = []
    top_still = []
    top_empty = []
    top_dialogue = []
    slow_by_segment = []
    camera_missing = 0
    camera_late = 0
    no_gaze = 0
    pub_over = 0
    warm_segments = 0

    for seg in segments:
        label = f"{seg['episode']}/{seg['shot']}"
        prompt = seg["prompt"]
        pub, timeline, _ = split_prompt(prompt)
        if pub and len(pub) / max(len(prompt), 1) > pub_max:
            pub_over += 1
            issues.append(
                {
                    "level": "warning",
                    "kind": "public_spec_bloat",
                    "segment": label,
                    "detail": f"公共总规范 {len(pub)/len(prompt):.0%} > {pub_max:.0%}",
                }
            )
        slow_count = prompt.count("极缓慢")
        if slow_count > max_extreme:
            slow_by_segment.append((label, slow_count, len(prompt)))
            issues.append(
                {
                    "level": "warning",
                    "kind": "extreme_slow",
                    "segment": label,
                    "detail": f"{slow_count} 处（上限 {max_extreme}）",
                }
            )
        for term in warm_terms:
            if term in prompt:
                warm_segments += 1
                issues.append(
                    {
                        "level": "warning",
                        "kind": "warm_light",
                        "segment": label,
                        "detail": term,
                    }
                )
                break
        has_char = any(c in prompt for c in CHARS)
        if has_char and not any(x in prompt for x in ("不看镜头", "不朝镜头", "视线避开镜头")):
            no_gaze += 1
            issues.append(
                {
                    "level": "warning",
                    "kind": "missing_no_lens_gaze",
                    "segment": label,
                    "detail": "有角色但无『不看镜头』",
                }
            )
        # Character looking at the lens is a blocker; an object "facing the
        # camera direction" is not. Require a character/body anchor nearby.
        for line in prompt.splitlines():
            if not POSITIVE_GAZE.search(line):
                continue
            if not any(c in line for c in CHARS + GROUPS + BODY):
                continue
            issues.append(
                {
                    "level": "error",
                    "kind": "positive_lens_gaze",
                    "segment": label,
                    "detail": POSITIVE_GAZE.search(line).group(0),
                }
            )

        fantasy_context = "幻境层" in prompt
        group_rows = 0
        for line in timeline.splitlines():
            line = line.strip()
            rm = ROW.match(line)
            if not rm:
                continue
            rows_total += 1
            start, end = float(rm.group(1)), float(rm.group(2))
            body = rm.group(3)
            dur = end - start
            if dur <= 0:
                issues.append(
                    {
                        "level": "error",
                        "kind": "non_positive_duration",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒",
                    }
                )

            if re.match(r"^\d+(?:\.5)?秒[，,]", body):
                issues.append(
                    {
                        "level": "warning",
                        "kind": "duplicate_timestamp_in_body",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：{body[:12]}",
                    }
                )

            for term, _ctx in blocking_hits(body, blocking_terms):
                issues.append(
                    {
                        "level": "error",
                        "kind": "forbidden_blocking",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：{term}",
                    }
                )

            if not CAMERA_PREFIX.match(body):
                camera_missing += 1
            shot = SHOT.search(body)
            if shot:
                pos = shot.start() / max(len(body), 1)
                if pos > camera_max:
                    camera_late += 1
                    issues.append(
                        {
                            "level": "warning",
                            "kind": "camera_late",
                            "segment": label,
                            "detail": f"{start:g}-{end:g}秒：镜头词在 {pos:.0%}",
                        }
                    )

            char_hit = any(c in body for c in CHARS + GROUPS)
            body_hit = any(b in body for b in BODY)
            prop_hit = any(p in body for p in PROPS)
            action_nodes = len(set(ACTION.findall(body)))
            has_dialogue = ('"' in body or "“" in body or "口型对白" in body)

            # --- 人物分身/身份预算（WAN30-02）---
            named_count = sum(1 for c in CHARS if c in body)
            five_group = bool(FIVE_GROUP.search(body))
            if named_count > max_named_faces:
                issues.append(
                    {
                        "level": "warning",
                        "kind": "identity_overload",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：{named_count} 个角色同框（上限 {max_named_faces}）",
                    }
                )
            if five_group and dur > max_five_sec:
                issues.append(
                    {
                        "level": "warning",
                        "kind": "five_person_shot_too_long",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒（{dur:g}s）：五人全景/群像超过 {max_five_sec:g}s",
                    }
                )
            if five_group and FACE_SHOT.search(body):
                issues.append(
                    {
                        "level": "warning",
                        "kind": "five_person_face_overload",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：五人同框叠正脸/近景",
                    }
                )
            if named_count >= 4 and has_dialogue and forbid_five_dialogue:
                issues.append(
                    {
                        "level": "warning",
                        "kind": "group_dialogue_overload",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：{named_count} 人同框说话",
                    }
                )
            if (
                reflection_tag
                and REFLECTION.search(body)
                and "幻境层" not in body
                and not fantasy_context
            ):
                issues.append(
                    {
                        "level": "warning",
                        "kind": "reflection_ambiguity",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：反射/复制词未标幻境层",
                    }
                )
            if named_count >= 4 or five_group:
                group_rows += 1

            is_empty = not char_hit and not body_hit and not has_dialogue
            if prop_hit and not char_hit and not body_hit:
                # Prop-only beat (no character, no body part) is a still-life
                # beat even if the paper corner moves a little; cap applies.
                if dur > still_max:
                    top_still.append((label, start, end, dur, body[:40]))
                    issues.append(
                        {
                            "level": "warning",
                            "kind": "still_life_too_long",
                            "segment": label,
                            "detail": f"{start:g}-{end:g}秒（{dur:g}s）",
                        }
                    )
            elif is_empty and dur > empty_max:
                top_empty.append((label, start, end, dur, body[:40]))
                issues.append(
                    {
                        "level": "warning",
                        "kind": "empty_shot_too_long",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒（{dur:g}s）",
                    }
                )
            if has_dialogue and dur > dialogue_max:
                top_dialogue.append((label, start, end, dur, body[:40]))
                issues.append(
                    {
                        "level": "warning",
                        "kind": "dialogue_shot_too_long",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒（{dur:g}s）",
                    }
                )
            if (
                TEXT_PROP.search(body)
                and CLOSE_UP.search(body)
                and TEXT_WORD.search(body)
            ):
                issues.append(
                    {
                        "level": "warning",
                        "kind": "legible_text_closeup_risk",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒",
                    }
                )
            if char_hit and dur >= 2.0 and action_nodes < min_action_nodes:
                issues.append(
                    {
                        "level": "warning",
                        "kind": "low_action_density",
                        "segment": label,
                        "detail": f"{start:g}-{end:g}秒：可见动作 {action_nodes} 个",
                    }
                )

        if group_rows > 1:
            issues.append(
                {
                    "level": "warning",
                    "kind": "group_shot_budget",
                    "segment": label,
                    "detail": f"本段 {group_rows} 个 4+ 人/五人同框拍（建议 ≤1）",
                }
            )

    counts = Counter(i["kind"] for i in issues)
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    return {
        "package": str(package),
        "segments": len(segments),
        "rows": rows_total,
        "errors": len(errors),
        "warnings": len(warnings),
        "counts": dict(sorted(counts.items())),
        "camera_missing_prefix": camera_missing,
        "camera_late": camera_late,
        "no_gaze_segments": no_gaze,
        "public_spec_over": pub_over,
        "warm_segments": warm_segments,
        "slow_by_segment": sorted(slow_by_segment, key=lambda x: -x[1])[:10],
        "top_still": sorted(top_still, key=lambda x: -x[3])[:10],
        "top_empty": sorted(top_empty, key=lambda x: -x[3])[:10],
        "top_dialogue": sorted(top_dialogue, key=lambda x: -x[3])[:10],
        "issues": issues,
    }


def print_human(result: dict, limit: int = 12) -> None:
    print("=" * 68)
    print(f"Wan3.0 反例审计｜{result['package']}")
    print("=" * 68)
    print(
        f"段数 {result['segments']}｜时间行 {result['rows']}｜"
        f"阻断 {result['errors']}｜警告 {result['warnings']}"
    )
    print(
        f"镜头未前置 {result['camera_missing_prefix']}/{result['rows']}｜"
        f"镜头词后置 {result['camera_late']} 行｜"
        f"缺『不看镜头』{result['no_gaze_segments']} 段｜"
        f"公共总规范超比 {result['public_spec_over']} 段｜"
        f"暖光词 {result['warm_segments']} 段"
    )
    print("\n问题计数：")
    for kind, n in result["counts"].items():
        print(f"  {kind}: {n}")

    def dump(title, items, fmt):
        print(f"\n{title}")
        if not items:
            print("  （无）")
            return
        for it in items[:limit]:
            print("  " + fmt(it))

    dump(
        "阻断项（必须清零）",
        [i for i in result["issues"] if i["level"] == "error"],
        lambda i: f"{i['segment']}｜{i['kind']}｜{i['detail']}",
    )
    dump(
        "最长静物拍（>2s）",
        result["top_still"],
        lambda x: f"{x[0]}｜{x[1]:g}-{x[2]:g}秒（{x[3]:g}s）｜{x[4]}…",
    )
    dump(
        "最长空镜（>2.5s）",
        result["top_empty"],
        lambda x: f"{x[0]}｜{x[1]:g}-{x[2]:g}秒（{x[3]:g}s）｜{x[4]}…",
    )
    dump(
        "最长台词单拍（>6s）",
        result["top_dialogue"],
        lambda x: f"{x[0]}｜{x[1]:g}-{x[2]:g}秒（{x[3]:g}s）｜{x[4]}…",
    )
    dump(
        "极缓慢最多的段",
        result["slow_by_segment"],
        lambda x: f"{x[0]}｜{x[1]} 次（{x[2]} 字符）",
    )
    print(
        "\n提示：本脚本为专项审计，不替代 validate_compact_package.py --model wan30；"
        "阻断项清零后才进入生成。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a Wan3.0 compact package for WAN30-01 anti-patterns."
    )
    parser.add_argument("package", type=Path, help="精简制作包 Markdown")
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "policy.json",
        help="policy.json 路径",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="警告也返回非零退出码（生成前建议开启）",
    )
    parser.add_argument("--limit", type=int, default=12, help="每类最多列几条")
    args = parser.parse_args()
    if not args.package.exists():
        print(f"找不到文件：{args.package}", file=sys.stderr)
        return 2
    result = audit(args.package, args.policy)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result, args.limit)
    if result["errors"]:
        return 1
    if args.strict and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
