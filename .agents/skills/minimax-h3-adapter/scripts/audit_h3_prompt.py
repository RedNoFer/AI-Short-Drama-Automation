#!/usr/bin/env python3
"""Audit a MiniMax H3 prompt for structural compliance.

只做格式机检：字段与顺序、模式对齐指令行、切点时间、说话人 ID、<d> 语言标签、
参考标签一致性、时长范围。剧情、表演与空间衔接仍需 agent 人工评审。

用法：
  python3 audit_h3_prompt.py 提示词.md [--mode base|ref2va] [--duration 15]
  python3 audit_h3_prompt.py 提示词.md --mode fl2va
"""

import argparse
import json
import re
import sys
from pathlib import Path

BASE_FIELDS = ["integrated_multimodal_description", "overall_soundscape", "non_diegetic_music"]
REF_FIELDS = [
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
]
MODES = {
    "t2va": ("base", False),
    "i2va": ("base", True),
    "fl2va": ("base", True),
    "l2va": ("base", True),
    "base": ("base", False),
    "ref2va": ("ref2va", False),
}
ALIGN_MARK = "aligns with the target video"
TIME_RE = re.compile(r"At\s+(\d{2}):(\d{2})\.(\d{3})")
SHOT_RE = re.compile(r"\[Shot\s+(\d+)\]")
SPEAKER_RE = re.compile(r"\((S\d+)\)")
DIALOG_RE = re.compile(r"<d>(.*?)</d>", re.S)
LABEL_RE = re.compile(r"<(Subject|Picture|Video|Audio)\s+(\d+)>")
ABSTRACT = re.compile(r"\b(beautiful|masterpiece|stunning|high[- ]quality|8k|ultra[- ]hd)\b", re.I)
ALIGN_RE = re.compile(r"align(?:s)?\s+with\s+the\s+target\s+video", re.I)


def section_bounds(text, field):
    """Return (start, end) span of a 'field:' block."""
    match = re.search(rf"^{field}\s*:", text, re.M)
    if not match:
        return None
    start = match.start()
    rest = text[match.end():]
    nxt = re.search(r"\n([A-Za-z_][A-Za-z0-9_]*)\s*:", rest)
    end = match.end() + (nxt.start() if nxt else len(rest))
    return start, end


def slice_field(text, field):
    bounds = section_bounds(text, field)
    if not bounds:
        return None
    start, end = bounds
    body = text[start:end]
    body = body.split(":", 1)[1] if ":" in body else body
    return body.strip()


def check_order(text, fields, errors):
    positions = []
    for field in fields:
        match = re.search(rf"^{field}\s*:", text, re.M)
        if not match:
            errors.append(f"缺少字段 `{field}`")
            positions.append(None)
        else:
            positions.append(match.start())
    known = [p for p in positions if p is not None]
    if len(known) == len(fields) and known != sorted(known):
        order = [f for f, p in zip(fields, positions)]
        errors.append(f"字段顺序不符，官方顺序为 {order}")


def check_alignment(text, mode, errors, warnings):
    first_field = None
    for field in ("integrated_multimodal_description", "detailed_description"):
        match = re.search(rf"^{field}\s*:", text, re.M)
        if match:
            first_field = match.start()
            break
    prelude = text[:first_field] if first_field is not None else text
    prelude_lines = [line for line in prelude.splitlines() if line.strip()]
    needs = mode in ("i2va", "fl2va", "l2va")
    has = bool(ALIGN_RE.search(prelude)) or any(
        line.strip().startswith("For the target video, at 0.00 seconds") for line in prelude_lines
    )
    if needs and not has:
        errors.append(f"{mode} 模式首行缺少官方关键帧对齐指令行")
    if not needs and has:
        warnings.append(f"{mode} 模式通常不需要对齐指令行，请确认是否误用")


def check_shots(body, duration, errors, warnings):
    shots = list(SHOT_RE.finditer(body))
    if not shots:
        errors.append("主体内没有找到 [Shot N] 镜头标记")
        return
    numbers = [int(m.group(1)) for m in shots]
    if numbers[0] != 1:
        errors.append(f"首个镜头编号应为 1，实际为 {numbers[0]}")
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"镜头编号应连续递增，实际为 {numbers}")
    times = []
    for index, match in enumerate(shots):
        segment_end = shots[index + 1].start() if index + 1 < len(shots) else len(body)
        segment = body[match.end():segment_end]
        stamp = TIME_RE.search(segment[:60])
        if index == 0:
            if stamp:
                errors.append("[Shot 1] 不应带时间戳")
            continue
        if not stamp:
            errors.append(f"[Shot {numbers[index]}] 缺少切点时间戳（At MM:SS.mmm）")
            continue
        minutes, seconds, millis = stamp.groups()
        value = int(minutes) * 60 + int(seconds) + int(millis) / 1000
        times.append((numbers[index], value))
    if times:
        previous = None
        for number, value in times:
            if previous is not None and value <= previous:
                errors.append(f"[Shot {number}] 切点时间未严格递增")
            previous = value
            if duration and value > duration:
                errors.append(f"[Shot {number}] 切点 {value:.3f}s 超出成片时长 {duration}s")
        last = times[-1][1]
        if duration and duration - last > 0.001 and not re.search(
            r"establish|settle|final composition|end of the shot", body[-400:], re.I
        ):
            warnings.append("最后一个切点与成片时长之间有较大间隔，确认结尾是否已描述")


def check_dialogue(body, errors, warnings):
    blocks = DIALOG_RE.findall(body)
    for index, block in enumerate(blocks, 1):
        content = block.strip()
        if not content.startswith("["):
            errors.append(f"第 {index} 处 <d> 缺少语言标签（如 <d>[English] ...</d>）")
            continue
        if not re.search(r"[.!?。？！]$", content):
            warnings.append(f"第 {index} 处 <d> 未以 . ? ! 收尾")
    if body.count("<d>") != body.count("</d>"):
        errors.append("存在未闭合的 <d> 标签")
    if "<scenetrans>" in body and not re.search(
        r"(continues|carries over|remains audible)", body, re.I
    ):
        errors.append("使用 <scenetrans> 时必须写明声音跨切延续")


def check_speakers(body, errors, warnings):
    ids = [m.group(1) for m in SPEAKER_RE.finditer(body)]
    if not ids:
        return
    numbers = sorted({int(i[1:]) for i in ids})
    if numbers[0] != 1:
        errors.append(f"说话人 ID 应从 S1 开始，实际出现 {sorted(set(ids))}")
    if numbers != list(range(1, len(numbers) + 1)):
        warnings.append(f"说话人 ID 不连续：{sorted(set(ids))}")
    if re.search(r"off-screen voiceover", body) and not re.search(
        r"lips? (remain|are) (completely )?closed", body, re.I
    ):
        errors.append("画外音必须写明嘴唇保持闭合")


def check_labels(text, body, ref_mode, errors, warnings):
    used = {}
    for match in LABEL_RE.finditer(body):
        used.setdefault(match.group(1), set()).add(int(match.group(2)))
    for kind, numbers in used.items():
        if sorted(numbers) != list(range(1, max(numbers) + 1)):
            errors.append(f"<{kind} N> 编号不连续：{sorted(numbers)}")
    if ref_mode:
        definitions = slice_field(text, "subject_definitions") or ""
        defined = {match.group(1): set() for match in LABEL_RE.finditer(definitions)}
        for match in LABEL_RE.finditer(definitions):
            defined[match.group(1)].add(int(match.group(2)))
        for kind, numbers in used.items():
            missing = numbers - defined.get(kind, set())
            if missing:
                errors.append(f"<{kind} {sorted(missing)}> 未在 subject_definitions 中定义")
        retention = slice_field(text, "retention_analysis") or ""
        if re.search(r"\(S\d+\)", retention):
            errors.append("retention_analysis 段不应出现说话人 ID")


def check_sound_fields(text, errors, warnings):
    for field, low, high in (("overall_soundscape", 1, 4), ("non_diegetic_music", 1, 3)):
        body = slice_field(text, field)
        if body is None:
            continue
        if body.strip().upper().startswith("N/A"):
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", body.strip()) if s.strip()]
        if not (low <= len(sentences) <= high):
            errors.append(f"{field} 应为 {low}–{high} 句，实际 {len(sentences)} 句")


def check_duration(duration, body, errors, warnings):
    if duration is None:
        stamps = [float(f"{m.group(2)}.{m.group(3)}") for m in TIME_RE.finditer(body)]
        if stamps:
            inferred = max(stamps)
            if inferred < 4 or inferred > 15:
                warnings.append(f"推断成片时长约 {inferred:.1f}s，超出 H3 的 4–15 秒范围")
        return
    if not (4 <= duration <= 15):
        errors.append(f"成片时长 {duration}s 超出 H3 的 4–15 秒范围")


def check_body_quality(body, errors, warnings, policy=None):
    if ABSTRACT.search(body):
        warnings.append("出现抽象形容词（cinematic/beautiful/8k 等），官方要求改写为具体视听细节")
    for token in ("【参数】", "720p", "1080p", "2K", "4K"):
        if token in body:
            warnings.append(f"正文出现生成参数 `{token}`，按本目录约定参数由应用设置承载")


def check_length(prompt, policy, errors, warnings):
    """官方未设提示词字符上限；本地按官方生产范例量级给硬顶与过简线。"""
    profile = (policy or {}).get("model_profiles", {}).get("h3", {})
    hard = profile.get("prompt_max_chars", 6000)
    low = profile.get("prompt_min_chars", 1200)
    if len(prompt) > hard:
        errors.append(f"提示词 {len(prompt)} 字符，超过本项目 H3 硬顶 {hard}"
                      f"（官方未设字符上限；官方生产范例 2500–4540 字符）")
    elif len(prompt) < low:
        warnings.append(f"提示词只有 {len(prompt)} 字符，低于 {low}；"
                        f"官方生产 prompt 普遍 2500+ 字符（教学示例约 900），过简会削弱画面与声音细节")


def audit(text, mode, duration, policy=None):
    errors, warnings = [], []
    family, _ = MODES[mode]
    fields = REF_FIELDS if family == "ref2va" else BASE_FIELDS
    check_order(text, fields, errors)
    if mode != "base":
        check_alignment(text, mode, errors, warnings)
    body_field = "detailed_description" if family == "ref2va" else "integrated_multimodal_description"
    body = slice_field(text, body_field)
    if body is None:
        errors.append(f"缺少主体字段 `{body_field}`")
        body = ""
    else:
        check_shots(body, duration, errors, warnings)
        check_dialogue(body, errors, warnings)
        check_speakers(body, errors, warnings)
        check_labels(text, body, family == "ref2va", errors, warnings)
        if family == "ref2va":
            words = len(body.split())
            if not (300 <= words <= 560):
                warnings.append(f"detailed_description 约 {words} 词，官方生成类任务建议 350–500 词")
    check_sound_fields(text, errors, warnings)
    check_duration(duration, body, errors, warnings)
    check_body_quality(body, errors, warnings)
    check_length(text, policy, errors, warnings)
    return {
        "ok": not errors,
        "mode": mode,
        "duration": duration,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="提示词文件（.md 或 .txt）")
    parser.add_argument("--mode", default="base", choices=sorted(MODES), help="H3 生成模式")
    parser.add_argument("--duration", type=float, default=None, help="成片时长（4–15 秒）")
    parser.add_argument("--policy", type=Path, default=None,
                        help="项目策略 JSON（读取 H3 字符口径；缺省用内置值）")
    args = parser.parse_args()
    try:
        text = open(args.path, encoding="utf-8").read()
    except OSError as exc:
        print(f"无法读取文件：{exc}", file=sys.stderr)
        return 2
    policy = None
    if args.policy and args.policy.is_file():
        try:
            policy = json.loads(args.policy.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"无法读取策略文件：{exc}", file=sys.stderr)
            return 2
    result = audit(text, args.mode, args.duration, policy)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
