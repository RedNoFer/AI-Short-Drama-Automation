#!/usr/bin/env python3
"""Check a single Markdown file against the compact drama importer and local prompt rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ASSET = re.compile(r"^### (角色|场景|道具|线索) ([A-Za-z][A-Za-z0-9_-]*)｜(.+)$")
EPISODE = re.compile(r"^## 剧集 ([A-Za-z][A-Za-z0-9_-]*)｜(.+)$")
SHOT = re.compile(r"^### 片段 ([A-Za-z][A-Za-z0-9_-]*)｜(\d+)秒｜(.+)$")
BINDING = re.compile(r"^(角色|场景|道具|线索)：(.*)$")
ROW = re.compile(r"^(?P<start>\d+)-(?P<end>\d+)秒[，,](?P<text>.+)$")
ROW_WAN = re.compile(r"^(?P<start>\d+(?:\.5)?)-(?P<end>\d+(?:\.5)?)秒[，,](?P<text>.+)$")
LEGACY_MARKER_ROW = re.compile(r"^\d+-\d+秒｜镜头\s")
SHOT_ID_IN_TIMELINE = re.compile(r"镜头\s+[A-Za-z]\d+-SH\d+-S\d+")
HEADINGS = ("【参考】", "【公共总规范】", "【时间轴】", "【收尾】")
KINDS = {"角色": "CHAR_", "场景": "LOC_", "道具": "PROP_", "线索": "CLUE_"}
FIELDS = {"视频提示词", "章节文案", "静帧提示词", "首帧提示词", "尾帧提示词"}
H3_BASE_FIELDS = ["integrated_multimodal_description", "overall_soundscape",
                  "non_diegetic_music"]
H3_REF_FIELDS = ["subject_definitions", "summary", "retention_analysis",
                 "detailed_description", "overall_soundscape", "non_diegetic_music"]
H3_SHOT = re.compile(r"\[Shot\s+(\d+)\]")
H3_TIME = re.compile(r"At\s+(\d{1,2}):(\d{2})\.(\d{3})")
H3_SPEAKER = re.compile(r"\((S\d+)\)")
H3_DIALOG = re.compile(r"<d>(.*?)</d>", re.S)
H3_LABEL = re.compile(r"<(Subject|Picture|Video|Audio)\s+(\d+)>")
H3_VOICE_ANCHOR = re.compile(
    r"\b(voice|tone|low|high|hoarse|husky|soft|calm|firm|steady|breathy|"
    r"whisper|gravelly|childlike|elderly|female|male|deep|thin)\b", re.I)


def _band(value, default):
    """Parse a '5-10' style band into a (min, max) tuple."""
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", str(value or ""))
    if not match:
        return default
    return int(match.group(1)), int(match.group(2))


def _h3_section(prompt, field):
    """Return the body text of an H3 'field:' block."""
    match = re.search(rf"^{field}\s*:", prompt, re.M)
    if not match:
        return None
    rest = prompt[match.end():]
    nxt = re.search(r"\n([A-Za-z_][A-Za-z0-9_]*)\s*:", rest)
    return (rest[:nxt.start()] if nxt else rest).strip()



def check_prompt(prompt: str, episode: str, shot: str, duration: int, bindings: dict,
                 policy: dict, errors: list[str], char_names: dict | None = None,
                 oner: bool = False, model: str = "seedance25",
                 warnings: list[str] | None = None, tier: str | None = None,
                 extra_fields: dict | None = None) -> dict:
    label = f"{episode}/{shot}"
    stats = {"episode": episode, "shot": shot, "model": model,
             "mode": "fight_oner" if oner else "standard", "characters": len(prompt)}
    if model == "h3":
        return check_h3_prompt(prompt, episode, shot, duration, bindings, policy,
                               errors, warnings, extra_fields=extra_fields)
    limit = policy["video"]["prompt_max_chars"]
    band = (policy["video"]["hard_cuts_min"], policy["video"]["hard_cuts_max"])
    if model == "wan30":
        limit = (policy.get("model_profiles", {}).get("wan30", {})
                 .get("prompt_max_chars", limit))
    tiers = policy["video"].get("prompt_quality_tiers", {})
    if tier and tier in tiers and model != "wan30":
        selected = tiers[tier]
        limit = selected.get("prompt_max_chars", limit)
        band = _band(selected.get("hard_cuts", ""), band)
    if oner:
        limit = (policy["video"].get("prompt_quality_tiers", {})
                 .get("tier3_full_xiaomo63", {}).get("prompt_max_chars", limit))
    if len(prompt) > limit:
        errors.append(f"{label}: 视频提示词 {len(prompt)} 字符，超过 {limit}")
    if re.search(r"@Image\s+\d+|@图片\d+", prompt):
        errors.append(f"{label}: 导入文件没有图片附件，不得预写 @Image/@图片 编号")
    if "【参数】" in prompt:
        errors.append(f"{label}: 不再使用【参数】段；剧集/片段/时长/画幅由片段标题与应用设置承载，画风并入【公共总规范】")
    positions = []
    for heading in HEADINGS:
        if prompt.count(heading) != 1:
            errors.append(f"{label}: {heading} 必须恰好出现一次")
            return stats
        positions.append(prompt.index(heading))
    if positions != sorted(positions):
        errors.append(f"{label}: 视频提示词五段顺序错误")
        return stats
    sections = {}
    for index, heading in enumerate(HEADINGS):
        end = positions[index + 1] if index + 1 < len(HEADINGS) else len(prompt)
        sections[heading] = prompt[positions[index] + len(heading):end].strip()
        if not sections[heading]:
            errors.append(f"{label}: {heading} 内容为空")
    for codes in bindings.values():
        for code in codes:
            if code not in sections["【参考】"]:
                errors.append(f"{label}: 【参考】缺少已绑定资产 {code}")
    rows = []
    for line in sections["【时间轴】"].splitlines():
        line = line.strip()
        if not line:
            continue
        if LEGACY_MARKER_ROW.search(line) or SHOT_ID_IN_TIMELINE.search(line):
            errors.append(f"{label}: 时间行不得保留镜头项目编号或「｜镜头…｜起始/硬切｜」字段（编号只存内部逐镜表，切镜写自然语言）：{line[:60]}")
            continue
        row_re = ROW_WAN if model == "wan30" else ROW
        matched = row_re.fullmatch(line)
        if matched is None:
            grain = "0.5 秒粒度" if model == "wan30" else "整数秒"
            errors.append(f"{label}: 镜头行无法解析（格式为「起-止秒，自然语言内容」，{grain}）：{line[:60]}")
        else:
            rows.append(matched)
            text = matched["text"]
            tags = policy.get("voice", {}).get("source_tags", [])
            if tags and any(quote in text for quote in ('"', "“", "”")):
                if not any(tag in text for tag in tags):
                    errors.append(f"{label}: 含台词的镜头行缺少声音来源标签（口型对白/心理独白/画外旁白/画外余音/画外延续/低声自语/混叠人声）")
                if policy.get("voice", {}).get("require_lip_state", True) and "口型" not in text:
                    errors.append(f"{label}: 含台词的镜头行缺少口型说明")
            style = policy.get("prompt_style", {})
            if style.get("forbid_shot_shorthand", True):
                if "→" in text:
                    errors.append(f"{label}: 镜头行禁止「→」箭头与名词堆叠，须写成自然语言句子：{text[:40]}")
                for literal in style.get("procedural_row_literals", []):
                    if literal and literal in text:
                        errors.append(f"{label}: 镜头行出现程序性写法「{literal}」，须把机位景别融进自然语言句子：{text[:40]}")
                        break
                opening = style.get("procedural_row_opening_regex")
                if opening and re.search(opening, text):
                    errors.append(f"{label}: 镜头行不得以景别参数开场（如「中景以侧45°固定机位拍下」），须先写画面与动作：{text[:40]}")
            micro = policy.get("micro_expression", {})
            if micro.get("enabled"):
                qualifiers = micro.get("smile_qualifiers", [])
                qualified = any(q in text for q in qualifiers)
                for word in micro.get("smile_risk_words", []):
                    if word in text and not qualified:
                        errors.append(f"{label}: 镜头行出现易被模型演成微笑的措辞「{word}」，须同句显式限定（如「嘴角不上扬，不出现微笑」）或改用「唇线维持平直」类说法：{text[:40]}")
                        break
                if warnings is not None and not qualified:
                    for word in micro.get("smile_watch_words", []):
                        if word in text:
                            warnings.append(f"{label}: 镜头行用了需判定的情绪词「{word}」：须确认该镜目标情绪极性确实包含它（如真相反转后的释然），否则视为微笑漂移风险并改写")
                            break
            max_rate = policy.get("voice", {}).get("max_hanzi_per_sec", 5.0)
            if max_rate and '"' in text:
                quoted = re.findall(r'"([^"]*)"', text)
                hanzi = sum(len(re.findall(r"[\u4e00-\u9fff]", part)) for part in quoted)
                span = float(matched["end"]) - float(matched["start"])
                if span > 0 and hanzi / span > max_rate:
                    exempt = policy.get("voice", {}).get("rate_exempt_keywords", [])
                    if not any(word in text for word in exempt):
                        errors.append(f"{label}: 台词语速 {hanzi / span:.2f} 字/秒（台词汉字/镜内秒）超 {max_rate}，须补速率申报或调整时长")
    if not rows:
        errors.append(f"{label}: 没有可解析的镜头行")
        return stats
    stats["camera_shots"] = len(rows)
    cuts = len(rows) - 1
    stats["hard_cuts"] = cuts
    if oner:
        for row in rows:
            if "硬切" in row["text"]:
                errors.append(f"{label}: 一镜到底段时间行不得出现「硬切」，拍点之间用运镜/焦点过渡衔接：{row['text'][:40]}")
        if len(rows) < 2:
            errors.append(f"{label}: 一镜到底段至少需要 2 个拍点行（拍点即镜内节拍，行间为运镜过渡）")
    else:
        for index, row in enumerate(rows[1:], 2):
            if "硬切" not in row["text"]:
                errors.append(f"{label}: 第 {index} 个时间行须用自然语言写明「硬切」引出新镜头（如「x-y秒，硬切，……」）")
        low, high = band
        if not low <= cuts <= high:
            errors.append(f"{label}: 硬切 {cuts} 次，不在 {low}–{high} 次范围")
    previous = 0.0
    for index, row in enumerate(rows, 1):
        start, end = float(row["start"]), float(row["end"])
        if abs(start - previous) > 1e-9:
            errors.append(f"{label}: 镜头 {index} 从 {start:g} 秒开始，应从 {previous:g} 秒开始")
        if end <= start:
            errors.append(f"{label}: 镜头 {index} 起止时间无效")
        if model == "wan30" and (abs(start * 2 - round(start * 2)) > 1e-9 or abs(end * 2 - round(end * 2)) > 1e-9):
            errors.append(f"{label}: 镜头 {index} 时间粒度须为 0.5 秒的整数倍")
        previous = end
    if abs(previous - duration) > 1e-9:
        errors.append(f"{label}: 时间轴止于 {previous:g} 秒，应止于 {duration} 秒")
    voice = policy.get("voice", {})
    if voice.get("voice_lock_in_public", False):
        marker = voice.get("voice_lock_marker", "声线锁定：")
        human_tags = voice.get("human_voice_tags", ["口型对白", "心理独白", "画外延续", "低声自语", "混叠人声"])
        narrator_tags = voice.get("narrator_tags", ["画外旁白", "画外余音"])
        human_rows = [
            row for row in rows
            if '"' in row["text"]
            and any(tag in row["text"] for tag in human_tags)
            and not any(tag in row["text"] for tag in narrator_tags)
        ]
        if human_rows:
            public = sections["【公共总规范】"]
            anchor = public.find(marker)
            if anchor < 0:
                errors.append(f"{label}: 含人声音频但【公共总规范】缺少「{marker}」声线锁定行（锚点须取自声线母版）")
            else:
                lock = public[anchor:]
                for row in human_rows:
                    # 说话人归属：先剥掉引号内台词（台词可能点到其他角色名），
                    # 再只在「行外恰好出现一个已绑定角色名」这一高置信情况下校验；
                    # 多人同框、反应镜、画外延续等归属模糊的行交 agent 评审，脚本不猜。
                    outside_quotes = re.sub(r'"[^"]*"', "", row["text"])
                    present = [
                        code for code in bindings.get("角色", [])
                        if (char_names or {}).get(code) and char_names[code] in outside_quotes
                    ]
                    if len(present) == 1:
                        code = present[0]
                        if code not in lock and char_names[code] not in lock:
                            errors.append(f"{label}: 镜头说话人 {char_names[code]}（{code}）未出现在声线锁定行：{row['text'][:40]}")
    return stats


def check_h3_prompt(prompt: str, episode: str, shot: str, duration: int, bindings: dict,
                    policy: dict, errors: list[str],
                    warnings: list[str] | None = None,
                    extra_fields: dict | None = None) -> dict:
    """Check a MiniMax H3 body (base three fields or Ref2VA six sections)."""
    label = f"{episode}/{shot}"
    profile = policy.get("model_profiles", {}).get("h3", {})
    stats = {"episode": episode, "shot": shot, "model": "h3", "mode": "",
             "characters": len(prompt)}
    limit = profile.get("prompt_max_chars", 6000)
    if len(prompt) > limit:
        errors.append(f"{label}: H3 视频提示词 {len(prompt)} 字符，超过本项目 H3 上限 {limit}"
                      f"（官方未设字符上限；官方生产范例 2500–4540 字符）")
    min_chars = profile.get("prompt_min_chars", 0)
    if min_chars and len(prompt) < min_chars:
        warnings.append(f"{label}: H3 视频提示词只有 {len(prompt)} 字符，"
                        f"低于 {min_chars}；官方生产 prompt 普遍 2500+ 字符（教学示例约 900），过简会削弱画面与声音细节")
    if re.search(r"@Image\s+\d+|@图片\d+", prompt):
        errors.append(f"{label}: 导入文件没有图片附件，不得预写 @Image/@图片 编号")
    for marker in HEADINGS:
        if marker in prompt:
            errors.append(f"{label}: H3 轨正文用官方字段结构，不写四段结构标记 {marker}")
            break
    is_ref = "subject_definitions:" in prompt
    fields = H3_REF_FIELDS if is_ref else H3_BASE_FIELDS
    stats["mode"] = "ref2va" if is_ref else "base"
    positions = []
    for field in fields:
        hits = [m.start() for m in re.finditer(rf"^{field}\s*:", prompt, re.M)]
        if len(hits) != 1:
            errors.append(f"{label}: H3 字段 `{field}` 必须恰好出现一次（当前 {len(hits)} 次）")
            continue
        positions.append(hits[0])
    if len(positions) == len(fields) and positions != sorted(positions):
        errors.append(f"{label}: H3 字段顺序不符，官方顺序为 {fields}")
    body = _h3_section(prompt, "detailed_description" if is_ref
                       else "integrated_multimodal_description")
    if body is None:
        errors.append(f"{label}: 缺少 H3 正文段 `"
                      f"{'detailed_description' if is_ref else 'integrated_multimodal_description'}`")
        body = ""
    has_align = bool(re.search(r"align(?:s)?\s+with\s+the\s+target\s+video", prompt, re.I)) \
        or prompt.strip().startswith("For the target video, at 0.00 seconds")
    if "<Picture" in prompt and not has_align and not is_ref:
        errors.append(f"{label}: 出现 <Picture N> 但缺官方关键帧对齐指令行"
                      f"（Ref2VA 不需要该指令行）")
    shots = list(H3_SHOT.finditer(body))
    if not shots:
        errors.append(f"{label}: H3 正文没有 [Shot N] 镜头标记")
    else:
        numbers = [int(s.group(1)) for s in shots]
        if numbers[0] != 1:
            errors.append(f"{label}: 首个镜头编号应为 1，实际 {numbers[0]}")
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{label}: 镜头编号应连续递增，实际 {numbers}")
        previous = None
        for index, shot_match in enumerate(shots):
            segment_end = shots[index + 1].start() if index + 1 < len(shots) else len(body)
            segment = body[shot_match.end():segment_end]
            stamp = H3_TIME.search(segment[:80])
            if index == 0:
                if stamp:
                    errors.append(f"{label}: [Shot 1] 不应带时间戳")
                continue
            if not stamp:
                errors.append(f"{label}: [Shot {numbers[index]}] 缺少切点时间戳（At MM:SS.mmm）")
                continue
            minutes, seconds, millis = stamp.groups()
            value = int(minutes) * 60 + int(seconds) + int(millis) / 1000
            if previous is not None and value <= previous:
                errors.append(f"{label}: [Shot {numbers[index]}] 切点时间未严格递增")
            previous = value
            if value >= duration + 1e-9:
                errors.append(f"{label}: [Shot {numbers[index]}] 切点 {value:.3f}s 超出片段时长 {duration}s")
        cuts = len(shots) - 1
        stats["camera_shots"] = len(shots)
        stats["hard_cuts"] = cuts
        low = profile.get("hard_cuts_min", 0)
        high = profile.get("hard_cuts_max", 6)
        if not low <= cuts <= high:
            errors.append(f"{label}: H3 硬切 {cuts} 次，不在 {low}–{high} 次范围")
    used: dict[str, set[int]] = {}
    for label_match in H3_LABEL.finditer(prompt):
        used.setdefault(label_match.group(1), set()).add(int(label_match.group(2)))
    for kind, numbers in used.items():
        if sorted(numbers) != list(range(1, max(numbers) + 1)):
            errors.append(f"{label}: <{kind} N> 编号不连续：{sorted(numbers)}")
    if is_ref:
        definitions = _h3_section(prompt, "subject_definitions") or ""
        defined: dict[str, set[int]] = {}
        for label_match in H3_LABEL.finditer(definitions):
            defined.setdefault(label_match.group(1), set()).add(int(label_match.group(2)))
        for kind, numbers in used.items():
            missing = numbers - defined.get(kind, set())
            if missing:
                errors.append(f"{label}: <{kind} {sorted(missing)}> 未在 subject_definitions 中定义")
        retention = _h3_section(prompt, "retention_analysis") or ""
        if re.search(r"\(S\d+\)", retention):
            errors.append(f"{label}: retention_analysis 段不应出现说话人 ID")
    speakers = H3_SPEAKER.findall(body)
    if speakers:
        ids = sorted({int(item[1:]) for item in speakers})
        if ids[0] != 1:
            errors.append(f"{label}: 说话人 ID 应从 S1 开始，实际 {sorted(set(speakers))}")
        if ids != list(range(1, len(ids) + 1)):
            warnings.append(f"{label}: 说话人 ID 不连续：{sorted(set(speakers))}")
        for speaker in ids:
            match = re.search(rf"\(S{speaker}\)", body)
            context = body[max(0, match.start() - 220):match.start()] if match else ""
            if not H3_VOICE_ANCHOR.search(context):
                warnings.append(f"{label}: 说话人 S{speaker} 首次出现缺音色/音高/语速锚点（官方要求可识别身份）")
    for index, block in enumerate(H3_DIALOG.findall(body), 1):
        content = block.strip()
        if not content.startswith("["):
            errors.append(f"{label}: 第 {index} 处 <d> 缺少语言标签（如 <d>[English] ...</d>）")
        elif not re.search(r"[.!?。？！]$", content):
            warnings.append(f"{label}: 第 {index} 处 <d> 未以 . ? ! 收尾")
    if body.count("<d>") != body.count("</d>"):
        errors.append(f"{label}: 存在未闭合的 <d> 标签")
    if "off-screen voiceover" in body and not re.search(
            r"lips? (remain|are) (completely )?closed", body, re.I):
        errors.append(f"{label}: 画外音须写明嘴唇保持闭合")
    for field, low_s, high_s in (("overall_soundscape", 1, 4),
                                 ("non_diegetic_music", 1, 3)):
        text = _h3_section(prompt, field)
        if text is None:
            continue
        if text.upper().startswith("N/A"):
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if not low_s <= len(sentences) <= high_s:
            errors.append(f"{label}: {field} 应为 {low_s}–{high_s} 句，实际 {len(sentences)} 句")
    bound_codes = [code for kind in ("角色", "场景", "道具")
                   for code in bindings.get(kind, [])]
    subject_count = len(used.get("Subject", set()))
    if bound_codes and subject_count == 0:
        if used.get("Picture"):
            warnings.append(f"{label}: 已绑定 {len(bound_codes)} 项资产，"
                            f"正文只用 <Picture N>（身份与场景由参考图承担），未写 <Subject N>；"
                            f"资产→标签映射须登记在内部表")
        else:
            errors.append(f"{label}: 已绑定 {len(bound_codes)} 项资产，"
                          f"但正文没有任何 <Subject N>/<Picture N> 参考标签")
    elif bound_codes and subject_count != len(bound_codes):
        errors.append(f"{label}: 已绑定 {len(bound_codes)} 项资产，正文有 {subject_count} 个 "
                      f"<Subject N>，必须一一对应（编号按 角色→场景→道具 顺序，映射登记在内部表）")
    fields = extra_fields or {}
    if is_ref:
        # Ref2VA 的 <Picture N> 是全参考素材（不要求等于首帧/尾帧），来源登记在内部映射表
        for number in sorted(used.get("Picture", set())):
            if number >= 3:
                warnings.append(f"{label}: <Picture {number}> 属全参考素材，"
                                f"来源须登记在内部映射表（本 MD 不携带图片附件）")
    else:
        for field_name, tag in (("首帧提示词", "<Picture 1>"), ("尾帧提示词", "<Picture 2>")):
            has_field = bool((fields.get(field_name) or "").strip())
            has_tag = tag in prompt
            if has_field and not has_tag:
                errors.append(f"{label}: 片段有「{field_name}」，正文必须出现 {tag} 引用该图")
            if not has_field and has_tag:
                errors.append(f"{label}: 正文出现 {tag} 但片段没有「{field_name}」；"
                              f"未上传的真实图片不得预写编号")
        for number in sorted(used.get("Picture", set())):
            if number >= 3:
                warnings.append(f"{label}: <Picture {number}> 在制作包内没有对应字段登记"
                                f"（本 MD 不携带图片附件），来源须登记在内部映射表")
    if is_ref:
        words = len(body.split())
        low_w, high_w = profile.get("detailed_description_words", [350, 500])
        if not low_w * 0.85 <= words <= high_w * 1.12:
            warnings.append(f"{label}: detailed_description 约 {words} 词，"
                            f"官方生成类任务建议 {low_w}–{high_w} 词")
    return stats


def _norm_name(name: str) -> str:
    """Normalize an asset name for comparison (case and spacing insensitive)."""
    return " ".join((name or "").casefold().split())


def _episode_number(code: str) -> int | None:
    """Return the numeric part of an episode code such as E07."""
    match = re.fullmatch(r"[Ee](\d+)", code or "")
    return int(match.group(1)) if match else None


def parse_structure(source: str) -> dict:
    """Parse the import skeleton of a compact package: assets, episodes, structure errors."""
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    errors: list[str] = []
    assets: list[dict] = []
    episodes: list[dict] = []
    scope = None
    current_asset = current_episode = current_shot = None
    field = None
    title_seen = False
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or (line.startswith("<!--") and line.endswith("-->")):
            continue
        if line == "# 精简制作包" and not title_seen:
            title_seen = True
            continue
        if not title_seen:
            errors.append("首个非空行必须是 # 精简制作包")
            break
        if line == "## 固定资产":
            scope, current_asset, current_shot, field = "assets", None, None, None
            continue
        episode_match = EPISODE.fullmatch(line)
        if episode_match:
            scope, current_asset, current_shot, field = "episode", None, None, None
            current_episode = {"code": episode_match[1], "name": episode_match[2].strip(),
                               "novel": "", "shots": []}
            episodes.append(current_episode)
            continue
        asset_match = ASSET.fullmatch(line)
        if scope == "assets" and asset_match:
            current_asset = {"kind": asset_match[1], "code": asset_match[2],
                             "name": asset_match[3].strip(), "prompt": ""}
            assets.append(current_asset)
            field = None
            continue
        if scope == "episode" and line == "### 小说原文" and current_episode and not current_shot:
            field = "novel"
            continue
        shot_match = SHOT.fullmatch(line)
        if scope == "episode" and current_episode and shot_match:
            current_shot = {"code": shot_match[1], "duration": int(shot_match[2]),
                            "name": shot_match[3].strip(), "bindings": {}, "prompts": {},
                            "oner": "一镜到底" in shot_match[3]}
            current_episode["shots"].append(current_shot)
            field = None
            continue
        if scope == "assets" and line == "#### 图片提示词" and current_asset:
            field = "asset_prompt"
            continue
        if current_shot and line.startswith("#### ") and line[5:] in FIELDS:
            field = line[5:]
            continue
        if line in ("```text", "~~~text"):
            if not field:
                errors.append(f"第 {index} 行 text 块缺少字段标题")
                continue
            fence = line[:3]
            end = index
            while end < len(lines) and lines[end].strip() != fence:
                end += 1
            if end == len(lines):
                errors.append(f"第 {index} 行 text 块缺少结束标记")
                break
            value = "\n".join(lines[index:end])
            if field == "novel":
                current_episode["novel"] = value
            elif field == "asset_prompt":
                current_asset["prompt"] = value
            else:
                current_shot["prompts"][field] = value
            field = None
            index = end + 1
            continue
        binding_match = BINDING.fullmatch(line)
        if current_shot and binding_match:
            codes = [item for item in re.split(r"[,，、\s]+", binding_match[2]) if item]
            current_shot["bindings"][binding_match[1]] = codes
            continue
        errors.append(f"第 {index} 行无法识别：{line[:60]}")
    return {"assets": assets, "episodes": episodes, "errors": errors}


def build_sequel_index(parsed: dict) -> dict:
    """Index a baseline package so a sequel can be checked against it."""
    by_code = {asset["code"]: asset for asset in parsed["assets"]}
    by_name: dict[tuple[str, str], list[dict]] = {}
    for asset in parsed["assets"]:
        by_name.setdefault((asset["kind"], _norm_name(asset["name"])), []).append(asset)
    episodes = {episode["code"]: episode for episode in parsed["episodes"]}
    return {"by_code": by_code, "by_name": by_name, "episodes": episodes}


def check_sequel(assets: list[dict], episodes: list[dict], index: dict,
                 errors: list[str], warnings: list[str]) -> set[str]:
    """Check a sequel package against the baseline package already imported into the project.

    Follows the online template's 续集规范: episode codes decide ownership, existing codes
    replace a whole episode; fixed assets are matched by name; asset codes must not collide
    with the ones the project already holds.
    """
    by_code, by_name, base_episodes = index["by_code"], index["by_name"], index["episodes"]
    reusable: set[str] = set()
    for episode in episodes:
        code = episode["code"]
        if code in base_episodes:
            errors.append(
                f"{code}: 续集包写了基线包已存在的剧集代码；导入到已有项目时会整集替换项目里的 {code}"
                "（续集只写新集代码，已存在的集不要重复写进本文件）")
    for asset in assets:
        code, kind, name = asset["code"], asset["kind"], asset["name"]
        base = by_code.get(code)
        if base:
            if base["kind"] != kind:
                errors.append(
                    f"{code}: 续集资产类型（{kind}）与基线包同代码资产（{base['kind']}）不同；"
                    "代码不能和项目已有资产代码冲突")
            elif _norm_name(base["name"]) != _norm_name(name):
                errors.append(
                    f"{code}: 续集资产名称「{name}」与基线包同代码资产「{base['name']}」不同；"
                    "改名或加后缀会新建重复资产，名称须与项目已有资产逐字一致")
            else:
                reusable.add(code)
                if (asset["prompt"].strip() and base["prompt"].strip()
                        and asset["prompt"].strip() != base["prompt"].strip()):
                    warnings.append(
                        f"{code}「{name}」: 图片提示词与基线包不同；项目里已有提示词时本包内容会被忽略"
                        "（导入时会给出提醒），确认后再改")
        for other in by_name.get((kind, _norm_name(name)), []):
            if other["code"] != code:
                errors.append(
                    f"{code}「{name}」: 基线包里同类型同名资产的代码是 {other['code']}；"
                    f"名称一致才会自动复用该资产的基准图，请沿用 {other['code']}")
    base_numbers = [number for number in (_episode_number(code) for code in base_episodes)
                    if number is not None]
    if base_numbers:
        last = max(base_numbers)
        for episode in episodes:
            number = _episode_number(episode["code"])
            if number is not None and number <= last:
                warnings.append(
                    f"{episode['code']}: 集号不大于基线包最大集号 E{last:02d}；"
                    "新集建议接续编号，且不得与项目已有集重复")
    return reusable


def validate(source: str, policy: dict, model: str = "seedance25",
             tier: str | None = None, h3_segments: str = "app",
             baseline: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    request_bytes = len(json.dumps(
        {"action": "apply", "source": source, "fileName": "精简制作包.md",
         "sourceHash": "0" * 64},
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))
    max_bytes = policy["delivery"]["import_request_max_bytes"]
    if request_bytes >= max_bytes:
        errors.append(f"导入请求约 {request_bytes} 字节，达到目标应用的 {max_bytes} 字节上限")
    parsed = parse_structure(source)
    assets: list[dict] = parsed["assets"]
    episodes: list[dict] = parsed["episodes"]
    errors.extend(parsed["errors"])
    reusable_codes: set[str] = set()
    if baseline:
        base_parsed = parse_structure(baseline)
        reusable_codes = check_sequel(assets, episodes, build_sequel_index(base_parsed),
                                      errors, warnings)

    if policy.get("voice", {}).get("voice_lock_consistency", False):
        voice_map: dict[str, str] = {}
        for match in re.finditer(r"声线锁定：(.+)", source):
            for part in match.group(1).strip().rstrip("。").split("；"):
                if "＝" not in part:
                    continue
                name, desc = part.split("＝", 1)
                name, desc = name.strip(), desc.strip()
                if name in voice_map and voice_map[name] != desc:
                    errors.append(f"声线锁定跨片段不一致：{name} 的锚点出现两种写法（母版只能维护一处，全量派生）")
                voice_map[name] = desc
    if not episodes:
        errors.append("至少需要一个剧集")
    codes: dict[str, str] = {}
    char_names: dict[str, str] = {}
    names: set[tuple[str, str]] = set()
    for asset in assets:
        code, kind = asset["code"], asset["kind"]
        if code in codes:
            errors.append(f"资产代码重复：{code}")
        codes[code] = kind
        if kind == "角色":
            char_names[code] = asset["name"]
        name_key = (kind, " ".join(asset["name"].casefold().split()))
        if name_key in names:
            errors.append(f"同类型资产名称重复：{asset['name']}")
        names.add(name_key)
        if not code.startswith(KINDS[kind]):
            errors.append(f"{code}: {kind}代码须以 {KINDS[kind]} 开头")
        if not asset["name"]:
            errors.append(f"{code}: 缺少资产名称")
        elif not asset["prompt"].strip():
            if code in reusable_codes:
                warnings.append(
                    f"{code}「{asset['name']}」: 图片提示词留空（续集复用基线包资产，"
                    "项目里已有提示词时以项目为准）")
            else:
                errors.append(f"{code}: 缺少资产名称或图片提示词")
        if kind in ("角色", "场景") and asset["prompt"].strip():
            ratio = policy["assets"]["character_ratio" if kind == "角色" else "scene_ratio"]
            if ratio not in asset["prompt"]:
                errors.append(f"{code}: 图片提示词缺少默认画幅 {ratio}")
            layout = "四视图" if kind == "角色" else "全景"
            if layout not in asset["prompt"]:
                errors.append(f"{code}: 图片提示词缺少默认{layout}版式")
    seen_episodes = set()
    stats = []
    for episode in episodes:
        episode_code = episode["code"]
        if episode_code in seen_episodes:
            errors.append(f"剧集代码重复：{episode_code}")
        seen_episodes.add(episode_code)
        if not episode["name"] or not episode["novel"].strip() or not episode["shots"]:
            errors.append(f"{episode_code}: 需要标题、逐字小说原文和至少一个片段")
        seen_shots = set()
        for shot in episode["shots"]:
            label = f"{episode_code}/{shot['code']}"
            if shot["code"] in seen_shots:
                errors.append(f"{label}: 本集片段代码重复")
            seen_shots.add(shot["code"])
            if not shot["name"] or shot["duration"] <= 0:
                errors.append(f"{label}: 需要标题和正整数时长")
            if model == "wan30":
                prof = policy.get("model_profiles", {}).get("wan30", {})
                dlo = prof.get("duration_min", 2)
                dhi = prof.get("duration_max", 30)
                if not dlo <= shot["duration"] <= dhi:
                    errors.append(f"{label}: 片段时长 {shot['duration']} 秒，不在 Wan3.0 允许的 {dlo}–{dhi} 秒范围")
            elif model == "h3":
                prof = policy.get("model_profiles", {}).get("h3", {})
                official_max = prof.get("official_clip_duration_max", 15)
                if h3_segments == "official":
                    dlo = prof.get("official_clip_duration_min", 4)
                    if not dlo <= shot["duration"] <= official_max:
                        errors.append(f"{label}: H3 片段时长 {shot['duration']} 秒，"
                                      f"不在官方单条上限 {dlo}–{official_max} 秒范围")
                elif shot["duration"] > official_max:
                    warnings.append(f"{label}: H3 片段时长 {shot['duration']} 秒，"
                                    f"超过官方单条输出上限 {official_max} 秒；"
                                    f"需由应用分段生成或拼接，跨段承接登记在内部表")
            else:
                default = policy["video"]["default_duration_sec"]
                if shot["duration"] != default:
                    errors.append(f"{label}: 片段时长须为当前项目默认 {default} 秒")
            if "视频提示词" not in shot["prompts"] or not shot["prompts"]["视频提示词"].strip():
                errors.append(f"{label}: 缺少视频提示词")
                continue
            for kind, bound in shot["bindings"].items():
                if kind == "场景" and len(bound) > 1:
                    errors.append(f"{label}: 每片段至多绑定一个场景")
                if len(bound) != len(set(bound)):
                    errors.append(f"{label}: {kind}绑定代码重复")
                for code in bound:
                    if codes.get(code) != kind:
                        errors.append(f"{label}: {kind}绑定不存在或类型不符：{code}")
            stats.append(check_prompt(shot["prompts"]["视频提示词"], episode_code,
                                      shot["code"], shot["duration"], shot["bindings"],
                                      policy, errors, char_names,
                                      oner=shot.get("oner", False), model=model,
                                      warnings=warnings, tier=tier,
                                      extra_fields={k: v for k, v in shot["prompts"].items()
                                                    if k != "视频提示词"}))
    return {"ok": not errors, "episodes": len(episodes), "segments": len(stats),
            "assets": len(assets), "import_request_bytes": request_bytes,
            "stats": stats, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验可导入的短剧精简制作包 Markdown")
    parser.add_argument("file", type=Path, help="已填写的精简制作包 Markdown 文件")
    parser.add_argument("--model", choices=["seedance25", "wan30", "h3"],
                        default="seedance25",
                        help="生成模型轨：seedance25（默认，整数秒/分档字数）、"
                             "wan30（0.5秒粒度/20000字符/2-30秒）、"
                             "h3（MiniMax H3 官方字段结构/4-15秒/毫秒切点）")
    parser.add_argument("--tier", choices=["tier1_standard", "tier2_xiaomo63",
                                           "tier3_full_xiaomo63"],
                        default=None,
                        help="Seedance 轨提示词档位（字符上限与硬切带）；"
                             "缺省按项目策略当前默认档")
    parser.add_argument("--h3-segments", choices=["app", "official"], default="app",
                        help="H3 轨片段时长口径：app（默认，沿用应用片段单位，不额外拆条）"
                             "或 official（强制 4–15 秒单条）")
    parser.add_argument("--sequel-baseline", type=Path, default=None,
                        help="续集基线包路径：已导入目标项目的上一集《精简制作包.md》。"
                             "提供后按线上模板的续集规范检查集代码归属、资产名称对齐与代码冲突")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()
    try:
        source = args.file.read_text(encoding="utf-8")
        policy = json.loads((Path(__file__).resolve().parent.parent / "policy.json").read_text())
        baseline = None
        if args.sequel_baseline:
            baseline = args.sequel_baseline.read_text(encoding="utf-8")
        result = validate(source, policy, model=args.model, tier=args.tier,
                          h3_segments=args.h3_segments, baseline=baseline)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"无法校验文件：{exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"精简制作包：{'通过' if result['ok'] else '失败'}；"
              f"{result['episodes']} 集、{result['segments']} 片段、{result['assets']} 项资产"
              + ("（续集校验）" if args.sequel_baseline else ""))
        for item in result["errors"]:
            print(f"  错误：{item}")
        for item in result.get("warnings", []):
            print(f"  提醒：{item}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
