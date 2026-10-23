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
# Uploaded-image numbers. The MD carries no image attachments, so Seedance
# and H3 tracks must not pre-write them; the Wan3.0 track legitimately
# binds real references with @ImageN and is checked for numbering and
# binding consistency instead.
IMAGE_NUMBER = re.compile(r"@(?:Image|图片)\s*\d+")
IMAGE_BINDING = re.compile(r"@(?:Image|图片)\s*(\d+)\s*[＝=]\s*([A-Za-z][A-Za-z0-9_-]*)")
H3_VOICE_ANCHOR = re.compile(
    r"\b(voice|tone|low|high|hoarse|husky|soft|calm|firm|steady|breathy|"
    r"whisper|gravelly|childlike|elderly|female|male|deep|thin)\b", re.I)

# Space layer (E28 / W18): the prompt body must stay in natural language, never
# leak SCENE_JSON internals, and agree with the shot overlays on cast and side.
SPACE_LEAK = re.compile(
    r"position\s*=|fov\s*=|posePreset|movementPath|SCENE_JSON|"
    r"\[\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\]|"
    r"坐标\s*[：:=（(]?\s*-?\d|朝向着?为\s*-?\d")
SPACE_DEFAULT_DIR = ("内部", "04b-站位图")

# Outfit variants (E30 / outfit-variants.md): a wearable costume is carried as a
# prop-type asset whose prompt declares its owner, so the app can bind it.
OUTFIT_TOP = ("西装", "礼服", "婚纱", "连衣裙", "制服", "孝服", "工装", "军装",
              "警服", "校服", "旗袍", "唐装", "中山装", "运动服", "风衣", "大衣",
              "夹克", "针织衫", "毛衣", "背心", "衬衫", "polo衫")
OUTFIT_OWNER = re.compile(r"供\s*(CHAR_[A-Za-z0-9_-]+)\s*穿着")
OUTFIT_MARK = re.compile(r"可穿戴服装|服装变体|可穿戴道具")
FIXED_OUTFIT = re.compile(r"固定服装[：:]\s*([^\n。]{0,80})")
GARMENT_VERB = (r"(?:穿|换上|换了|套上|套着|身穿|穿着|穿了一身|穿着一身|脱下|脱掉|换到"
                r"|这身|那身)")
CHANGE_VERB = re.compile(r"换上|脱下|脱掉|换到|套上|换了一身|改穿")
# Words that imply a different garment from the character's default look.
# 场合级（身份/职务/仪式）服装词。「工装」是款式类别而非场合级制服（工装夹克/工装裤
# 是角色的固定装，不构成服装变体），故只收「工装服」。
VARIANT_WORDS = ("西装", "礼服", "婚纱", "连衣裙", "孝服", "军装", "警服", "旗袍",
                 "唐装", "中山装", "校服", "运动服", "工装服")


def _pronoun_words(line: str) -> set:
    """Clothing words worn by the only speaker in a single-character fragment."""
    found: set = set()
    pattern = re.compile(
        r"(?<![其])(?:他|她)[^。！？\n]{0,2}?" + GARMENT_VERB +
        r"[^。！？\n]{0,10}?(" + "|".join(OUTFIT_TOP) + r")")
    for match in pattern.finditer(line):
        found.add(match.group(1))
    return found


def _attributed_words(line: str, name: str) -> set:
    """Clothing words explicitly worn by this character in one line.

    Only patterns that state the wearer count. A name merely appearing in the
    same line as someone else's coat must not be counted.
    """
    found: set = set()
    pattern = re.compile(
        re.escape(name) + r"[^。！？\n]{0,4}?" + GARMENT_VERB +
        r"[^。！？\n]{0,10}?(" + "|".join(OUTFIT_TOP) + r")")
    for match in pattern.finditer(line):
        found.add(match.group(1))
    reverse = re.compile(
        "(" + "|".join(OUTFIT_TOP) + r")[^。！？\n]{0,6}?(?:穿在|上身|属于|是|套在)"
        r"[^。！？\n]{0,4}?" + re.escape(name))
    for match in reverse.finditer(line):
        found.add(match.group(1))
    possessive = re.compile(
        re.escape(name) + r"[^。！？\n]{0,3}?的(" + "|".join(OUTFIT_TOP) + r")")
    for match in possessive.finditer(line):
        found.add(match.group(1))
    return found


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
                 extra_fields: dict | None = None,
                 asset_codes: set | None = None,
                 asset_prompts: dict | None = None) -> dict:
    label = f"{episode}/{shot}"
    asset_prompts = asset_prompts or {}
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
    if model != "wan30" and IMAGE_NUMBER.search(prompt):
        errors.append(f"{label}: 导入文件没有图片附件，不得预写 @Image/@图片 编号"
                      "（本轨用资产代码点名；Wan3.0 轨才允许 @Image 多模态参考）")
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
    if model == "wan30":
        pairs = IMAGE_BINDING.findall(sections["【参考】"])
        numbers = [int(number) for number, _ in pairs]
        if numbers:
            if sorted(numbers) != list(range(1, len(numbers) + 1)):
                errors.append(
                    f"{label}: @Image 编号必须从 1 连续编号，当前为 {sorted(numbers)}")
            bound_all = {c for codes in bindings.values() for c in codes}
            # 角色的视频参考形态：CHAR_0X_PHOTO 是 CHAR_0X 的「单张电影剧照」形态。
            # 段头绑定的是角色身份资产（CHAR_0X），参考绑的是该角色的剧照——
            # 同一角色，绑定了身份即视为已绑定该角色的剧照。
            for number, code in pairs:
                if asset_codes is not None and code not in asset_codes:
                    errors.append(
                        f"{label}: @Image{number} 指向 {code}，但该资产在固定资产区没有定义")
                    continue
                base = code[:-6] if code.endswith("_PHOTO") else code
                if code in bound_all or base in bound_all:
                    continue
                warnings.append(
                    f"{label}: @Image{number} 指向 {code}，该资产未绑定到本片段"
                    "（跨场承接引用时属正常，确认不是漏绑）")
            # 本轨硬规则：视频参考不得是白底四视图设定板（WAN30-01 硬规则 1）
            for number, code in pairs:
                prompt = asset_prompts.get(code, "")
                if prompt and "四视图" in prompt and "不是四视图" not in prompt:
                    errors.append(
                        f"{label}: @Image{number} 指向 {code}，但该角色资产是白底四视图设定板——"
                        "本轨视频参考必须是单张场景内电影剧照（WAN30-01 硬规则 1）")
    rows = []
    thin_shots = []
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
                share_limit = policy.get("voice", {}).get("dialogue_share_warn", 0.0)
                if share_limit and span > 0 and hanzi:
                    share_exempt = policy.get("voice", {}).get("dialogue_share_exempt_keywords", [])
                    if not any(word in text for word in share_exempt):
                        share = (hanzi / max_rate) / span
                        if share > share_limit:
                            thin_shots.append((matched["start"], share))
    if thin_shots and warnings is not None:
        share_limit = policy.get("voice", {}).get("dialogue_share_warn", 0.75)
        worst_at, worst = max(thin_shots, key=lambda item: item[1])
        warnings.append(
            f"{label}: {len(thin_shots)} 镜台词占镜内时长超过 {share_limit:.0%}"
            f"（最紧一镜起于 {worst_at} 秒、占到 {worst:.0%}），镜内没有动作余量；"
            "按 S02 口径台词之外还须留出动作与呼吸，须拆台词或补动作镜")
    if not rows:
        errors.append(f"{label}: 没有可解析的镜头行")
        return stats
    stats["camera_shots"] = len(rows)
    # 硬切按正文实际「硬切」标记计数，不用 len(rows)-1 代理——
    # 首拍误写「硬切」时代理数会少 1，掩盖超带。
    cuts = sum(1 for row in rows[1:] if "硬切" in row["text"])
    if rows and "硬切" in rows[0]["text"]:
        errors.append(f"{label}: 首拍不得写「硬切」——首镜直写开场画面，硬切只用于其后每一拍引出新镜头：{rows[0]['text'][:40]}")
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
    # 公共总规范自报的「全段 N 拍 N-1 次硬切」须与正文一致
    public_block = sections.get("【公共总规范】", "")
    declared = re.search(r"全段\s*(\d+)\s*拍\s*(\d+)\s*次硬切", public_block)
    if declared:
        d_shots, d_cuts = int(declared.group(1)), int(declared.group(2))
        if d_shots != len(rows) or d_cuts != cuts:
            errors.append(f"{label}: 公共总规范声明「全段 {d_shots} 拍 {d_cuts} 次硬切」与正文不符"
                          f"（正文 {len(rows)} 拍 {cuts} 次硬切）")
    # 4 人以上同框必须有人数锁定句（WAN30-02 第 3 条）
    lock_re = re.compile(r"(画面内|镜内|画面上)[^。；\n]{0,6}恰好[一二三四五]人")
    fuzzy_re = re.compile(r"其余[三四五六七八九]人|另外[三四五六七八九]道身影|其余人")
    for index, row in enumerate(rows, 1):
        body = row["text"]
        # 「（空间：…）」是站位层编译出的机位元数据，不是正文点名；
        # 统计具名人数/人数锁定句时必须先剥掉，否则会把画外说明误当成新增角色。
        core = body.split("（空间：")[0]   # 子句内含括号（如「（坐驾驶位）」），不能用 [^）]*
        named = sum(1 for name in ("阿泽", "苏晚", "老杨", "许棠", "小林", "黑衣人") if name in core)
        # 五人群像：数词后必须紧跟群像/站位类名词（避免把「五个人各自…」误判为群像镜）
        five = re.search(r"(?:五(?:人|名|道|个)(?:人|道|个)?(?:全景|远景|剪影|群像|同框|人影|身影|围拢|站|立|俯身|并肩|错开|散在|散落|不动)|[四五六]个人(?:各自|同时|一齐|陆续|先后|都|沉默|错开|散开|散立|不动|上车|下车|错落|围拢|散在|站在|围在|挤在|依次|一前排|排成|在)|[四五六](?:名|个|道)(?:人|身影|人影|剪影|轮廓)|[四五六]人(?:的|各|在|错))", body)
        if (named >= 4 or five) and not lock_re.search(core):
            errors.append(f"{label}: 第 {index} 个时间行（具名 {named} 人{'、含五人群像' if five else ''}）须写人数锁定句"
                          "（三人如「本镜画面内恰好三人：左起阿泽、苏晚、老杨；每人只有一个身体、一张脸；不出现第四人。」；"
                          "五人只点名三人、另两人按服装定位，如「本镜画面内恰好五人：左起苏晚、老杨、阿泽、黑色机能马甲的年轻女性、亮蓝防风外套的少年；每人只有一个身体、一张脸；不出现第六人。」）")
        fuzzy = fuzzy_re.search(core)
        if fuzzy and (named >= 4 or five):
            errors.append(f"{label}: 第 {index} 个时间行用了模糊指代「{fuzzy.group(0)}」，"
                          "须改为逐个点名并给左起位置（WAN30-02 第 3 条）")
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
    if IMAGE_NUMBER.search(prompt):
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


def _check_character_prompt_fields(asset: dict, policy: dict, warnings: list) -> None:
    """Soft-check the art-direction fields of a character image prompt.

    Only reports missing dimensions; it never judges whether the detail is any
    good. 「素颜」and 「无饰品」count as decisions, because a character with no
    makeup or ornaments still has to say so explicitly.
    """
    spec = policy.get("assets", {})
    groups = spec.get("character_prompt_groups", {})
    if not groups:
        return
    body = asset["prompt"]
    missing = []
    for label, words in groups.items():
        if not any(word in body for word in words):
            missing.append(label)
    parts = spec.get("face_parts", [])
    face_min = spec.get("face_parts_min", 0)
    if parts and face_min:
        absent = [part for part in parts if part not in body]
        if len(parts) - len(absent) < face_min:
            missing.append("眉眼鼻唇缺" + "、".join(absent) + "的相对关系")
    if missing:
        warnings.append(
            f"{asset['code']}「{asset['name']}」: 角色图片提示词缺少美工字段——"
            + "；".join(missing)
            + "（素颜、无饰品也须写明；字段在场不等于写得好）")


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


def _space_overlays(space_dir: Path) -> dict:
    """Index shot overlays by (episode, fragment): {'E01': {'SH01': [doc, ...]}}."""
    index: dict[str, dict[str, list[dict]]] = {}
    if not space_dir.is_dir():
        return index
    for path in sorted(space_dir.rglob("*.json")):
        if path.name.startswith("SCENE_") or path.name.startswith("_"):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        shot = str(doc.get("shot") or "")
        parts = shot.split("_")
        if len(parts) < 3:
            continue
        episode, fragment = parts[0], parts[1]
        index.setdefault(episode, {}).setdefault(fragment, []).append(doc)
    for episodes in index.values():
        for docs in episodes.values():
            docs.sort(key=lambda d: str(d.get("shot")))
    return index


def _space_screen_side(overlay: dict, position: list) -> str:
    """Which side of the frame a character sits on, from the overlay camera."""
    camera = overlay.get("camera") or {}
    cam = camera.get("position") or []
    target = camera.get("target") or []
    if len(cam) < 3 or len(target) < 3:
        return ""
    fx, fz = target[0] - cam[0], target[2] - cam[2]
    length = (fx * fx + fz * fz) ** 0.5
    if length < 1e-6:
        return ""
    fx, fz = fx / length, fz / length
    right_x, right_z = -fz, fx
    dx, dz = position[0] - cam[0], position[2] - cam[2]
    offset = dx * right_x + dz * right_z
    if abs(offset) < 0.25:
        return ""
    return "右" if offset > 0 else "左"


_RISK_ROW = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒[，,](.*)$", re.M)
_RISK_LOCK = re.compile(r"本镜画面内恰好([一二三四五六])人")
_RISK_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


def risk_shot_count(parsed: dict, char_names: dict) -> int:
    """命中风险闸门（画内 ≥2 人）的时间行数量，供「缺站位层即判错」使用。"""
    names = [n for n in char_names.values() if n]
    if not names:
        names = list(char_names.keys())
    total = 0
    for episode in parsed.get("episodes", []):
        for shot in episode.get("shots", []):
            text = shot.get("prompts", {}).get("视频提示词", "")
            for m in _RISK_ROW.finditer(text):
                body = m.group(3)
                lock = _RISK_LOCK.search(body)
                n = _RISK_CN.get(lock.group(1), 0) if lock else 0
                if n == 0:
                    n = sum(1 for nm in names if nm in body)
                if n >= 2:
                    total += 1
    return total


def space_exempted(pkg_path: Path) -> bool:
    """输入单登记「站位层：豁免」才允许不建站位层（默认必须建）。"""
    if pkg_path is None:
        return False
    internal = pkg_path.resolve().parent / "内部"
    for pat in ("00-*输入单*.md", "00-*.md"):
        for f in sorted(internal.glob(pat)):
            try:
                if "站位层：豁免" in f.read_text(encoding="utf-8") or "站位层: 豁免" in f.read_text(encoding="utf-8"):
                    return True
            except OSError:
                continue
    return False


def check_space_sync(parsed: dict, char_names: dict, space_dir: Path,
                     model: str = "seedance25") -> tuple[list[str], list[str], dict]:
    """Cross-check the prompt body against the SCENE_JSON shot overlays.

    Five checks per fragment that has a space layer:
      1. overlay count must equal the number of shot lines in the body
      2. every overlay timecode must match the body time line it covers
      3. the body must not leak SCENE_JSON internals (coordinates, pose ids)
      4. every character physically in frame must be bound in the fragment
      5. a left/right claim in the body must not contradict the overlay geometry
    """
    errors: list[str] = []
    warnings: list[str] = []
    stats = {"fragments": 0, "overlays": 0, "space_dir": str(space_dir)}
    index = _space_overlays(space_dir)
    if not index:
        stats["status"] = "skipped"
        return errors, warnings, stats
    stats["status"] = "checked"
    name_to_code = {}
    for code, name in char_names.items():
        if not name:
            continue
        name_to_code[name] = code
        # 资产名常带括注（「阿泽（全队领队）」），站位层只写主名
        base = re.split(r"[（(]", name, maxsplit=1)[0].strip()
        if base:
            name_to_code.setdefault(base, code)
    for episode in parsed["episodes"]:
        episode_code = episode["code"]
        fragments = index.get(episode_code)
        if not fragments:
            continue
        for shot in episode["shots"]:
            overlays = fragments.get(shot["code"])
            if not overlays:
                continue
            label = f"{episode_code}/{shot['code']}"
            prompt = shot["prompts"].get("视频提示词", "")
            stats["fragments"] += 1
            stats["overlays"] += len(overlays)

            if model == "h3":
                rows = H3_SHOT.findall(prompt)
                body_rows = []
            else:
                pattern = ROW_WAN if model == "wan30" else ROW
                body_rows = [m for m in prompt.split("\n") if pattern.match(m.strip())]
                rows = body_rows

            if model != "h3":
                # 站位层按 W18 只覆盖命中风险闸门的镜头，不要求全量；
                # 因此按 shot 编号（E##_SH##_S##）对齐，而不是按出现顺序 zip。
                by_index = {}
                for idx, row in enumerate(rows, 1):
                    match = pattern.match(row.strip())
                    if match:
                        by_index[idx] = f"{match.group('start')}-{match.group('end')}"
                covered = set()
                for overlay in overlays:
                    shot_id = str(overlay.get("shot") or "")
                    tail = re.search(r"_S(\d+)$", shot_id)
                    if not tail:
                        errors.append(
                            f"{label}: 站位增量 {shot_id or '(缺 shot 字段)'} 的编号不符合 "
                            "E##_SH##_S## 格式，无法与正文镜头对齐")
                        continue
                    idx = int(tail.group(1))
                    want = by_index.get(idx)
                    if want is None:
                        errors.append(
                            f"{label}: 站位增量 {shot_id} 指向存在的镜头之外"
                            f"（本段共 {len(rows)} 个镜头）")
                        continue
                    covered.add(idx)
                    got = str(overlay.get("timecode", ""))
                    if got and got != want:
                        errors.append(
                            f"{label}: 站位增量 {shot_id} 的时间码 {got} "
                            f"与正文 S{idx:02d} 时间行 {want} 不一致")
                stats.setdefault("coverage", {})[label] = (
                    f"{len(covered)}/{len(rows)}")

            leak = SPACE_LEAK.search(prompt)
            if leak:
                errors.append(
                    f"{label}: 正文出现站位 JSON 内部写法「{leak.group(0)}」，"
                    "交付包只写自然语言站位描述")

            bound = set(shot["bindings"].get("角色", []))
            for overlay in overlays:
                for char in overlay.get("characters") or []:
                    if not char.get("inFrame"):
                        continue
                    name = str(char.get("name") or "")
                    code = name_to_code.get(name)
                    if not code:
                        # 剪影（黑衣人）不是角色资产：只靠布光与雨幕处理，不要求绑定
                        if not char.get("silhouette"):
                            warnings.append(
                                f"{label}: 站位增量 {overlay.get('shot')} 标记 {name} 在画内，"
                                "但制作包没有同名角色资产")
                    elif code not in bound:
                        errors.append(
                            f"{label}: {name} 在站位增量里位于画内（{overlay.get('shot')}），"
                            f"但片段未绑定 {code}")
                    position = char.get("position") or []
                    if len(position) < 3:
                        continue
                    side = _space_screen_side(overlay, position)
                    if not side:
                        continue
                    # 名字与被判定的方位之间若夹着另一个角色名，左右属于后一个人
                    # （「阿泽居中、老杨在他左侧」），不能算到前一个人头上。
                    # 只认「名字…在/位于 + 画面左/右侧」这种方位句；
                    # 「转向右后方」是动作、「坐在他左侧」是座位，都不算画面方位。
                    claim = re.search(
                        re.escape(name) + r"([^。！？\n]{0,6}?)[在位于落在][^。！？\n]{0,3}?(?:画面)?(左|右)(侧|边)",
                        prompt)
                    gap = claim.group(1) if claim else ""
                    if claim and (any(
                            other in gap
                            for other in ("阿泽", "苏晚", "老杨", "许棠", "小林", "黑衣人")
                            if other != name)
                            or "、" in gap          # 「…的黑衣人影、画面右侧是阿泽」：左右属于下一项
                            or any(k in gap for k in ("坐", "躺", "蹲", "靠"))):  # 座位／姿态关系，不是画面方位
                        claim = None
                    if claim and claim.group(2) != side:
                        warnings.append(
                            f"{label}: 正文写「{name}」在画面{claim.group(2)}侧，"
                            f"站位增量算出的位置在{side}侧（镜头 {overlay.get('shot')}）")
                    if name and name not in prompt:
                        warnings.append(
                            f"{label}: 站位增量标记 {name} 在画内（{overlay.get('shot')}），"
                            "但正文没有提到这个人")
    return errors, warnings, stats


def check_outfit_consistency(parsed: dict, char_names: dict,
                             errors: list[str], warnings: list[str]) -> dict:
    """Check that costume changes are carried as wearable assets, not lost.

    An outfit variant is registered as a prop-type asset whose image prompt
    declares its owner (``供 CHAR_02 穿着``). Five checks per fragment:
      A. a costume word in the shot lines without any bound outfit asset
      B. a bound outfit asset whose owner is not in the fragment cast
      C. a bound outfit asset not marked with its owner in 【参考】
      D. one character wearing two different top garments in one fragment
      E. a costume word contradicting the character's own fixed outfit
    """
    assets = {asset["code"]: asset for asset in parsed["assets"]}
    outfits: dict[str, str] = {}
    for code, asset in assets.items():
        if asset["kind"] != "道具":
            continue
        prompt = asset.get("prompt", "")
        owner = OUTFIT_OWNER.search(prompt)
        if owner or OUTFIT_MARK.search(prompt):
            outfits[code] = owner.group(1) if owner else ""
    stats = {"outfit_assets": len(outfits), "fragments": 0, "outfit_bound": 0}
    for episode in parsed["episodes"]:
        for shot in episode["shots"]:
            label = f"{episode['code']}/{shot['code']}"
            prompt = shot["prompts"].get("视频提示词", "")
            if not prompt.strip():
                continue
            stats["fragments"] += 1
            bound_props = shot["bindings"].get("道具", [])
            bound_chars = shot["bindings"].get("角色", [])
            bound_outfits = [code for code in bound_props if code in outfits]
            stats["outfit_bound"] += len(bound_outfits)

            timeline = prompt.split("【时间轴】")[-1].split("【收尾】")[0]
            reference = prompt.split("【参考】")[-1].split("【公共总规范】")[0]

            for code in bound_outfits:
                owner = outfits[code]
                if owner and owner not in bound_chars:
                    errors.append(
                        f"{label}: 服装资产 {code} 声明供 {owner} 穿着，"
                        f"但本片段没有绑定 {owner}")
                owner_name = char_names.get(owner, "")
                entry = ""
                for line in reference.splitlines():
                    if code in line:
                        entry = line
                        break
                if owner and owner_name and owner_name not in entry and owner not in entry:
                    errors.append(
                        f"{label}: 服装资产 {code} 在【参考】里没有写明由谁穿着"
                        f"（应写 {owner} 或 {owner_name}）")

            variant_words = [word for word in VARIANT_WORDS if word in timeline]
            per_char: dict = {}
            for char_code in bound_chars:
                name = char_names.get(char_code)
                if not name:
                    continue
                worn: set = set()
                for line in timeline.splitlines():
                    worn |= _attributed_words(line, name)
                if worn:
                    per_char[name] = worn
            single = len(bound_chars) == 1
            if single:
                only = char_names.get(bound_chars[0])
                if only:
                    # Only one character in frame: every garment word belongs to them.
                    per_char[only] = {word for word in OUTFIT_TOP if word in timeline}

            for name, worn in per_char.items():
                if len(worn) <= 1:
                    continue
                lines_of = [line for line in timeline.splitlines() if name in line]
                if single:
                    lines_of = timeline.splitlines()
                has_change = any(CHANGE_VERB.search(line) for line in lines_of)
                if has_change:
                    warnings.append(
                        f"{label}: {name} 在同一片段换了装「{'、'.join(sorted(worn))}」，"
                        "须在镜头行给出镜内可见的换装动作来源")
                else:
                    errors.append(
                        f"{label}: {name} 在同一片段出现多套上装「{'、'.join(sorted(worn))}」"
                        "且无换装动作，一个片段内不能换装")

            owners = {outfits[code] for code in bound_outfits if outfits.get(code)}
            for char_code in bound_chars:
                name = char_names.get(char_code)
                asset = assets.get(char_code)
                if not name or not asset:
                    continue
                if char_code in owners:
                    # A bound outfit supersedes the character's default look.
                    continue
                worn = per_char.get(name, set())
                if not worn:
                    continue
                fixed = FIXED_OUTFIT.search(asset.get("prompt", ""))
                if not fixed:
                    continue
                locked = {word for word in OUTFIT_TOP if word in fixed.group(1)}
                clash = worn - locked
                if clash:
                    errors.append(
                        f"{label}: {name} 的角色资产锁定「{fixed.group(1).strip()[:26]}」，"
                        f"镜头行却写成「{'、'.join(sorted(clash))}」——"
                        "须补服装变体资产并在【参考】写明谁穿，或改回锁定装")

            if variant_words and not bound_outfits:
                warnings.append(
                    f"{label}: 镜头行出现场合级服装词「{'、'.join(sorted(set(variant_words)))}」"
                    "但本片段没有绑定服装变体资产（服装须单独出图并写明谁穿）")
    return stats


def validate(source: str, policy: dict, model: str = "seedance25",
             tier: str | None = None, h3_segments: str = "app",
             baseline: str | None = None,
             space_dir: Path | None = None,
             space_exempt: bool = False) -> dict:
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
    asset_prompts: dict[str, str] = {}
    names: set[tuple[str, str]] = set()
    for asset in assets:
        code, kind = asset["code"], asset["kind"]
        if code in codes:
            errors.append(f"资产代码重复：{code}")
        codes[code] = kind
        if kind == "角色":
            char_names[code] = asset["name"]
        asset_prompts[code] = asset["prompt"]
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
        if kind == "道具" and asset["prompt"].strip() and re.search(r"[字条纸条便签沙字字痕]", asset["name"]):
            # 带字道具：资产图不得要求可读汉字（图片模型渲染中文必错）
            if re.search(r"可读|可辨读|端正|正确的中文", asset["prompt"]) and \
                    not re.search(r"不要|不构成|不可辨读|不得", asset["prompt"]):
                warnings.append(f"{code}「{asset['name']}」: 带字道具的资产图不应要求可读文字——"
                                "资产图只给抽象墨痕/笔道形态，实际文字由提示词层声明")
        if kind in ("角色", "场景") and asset["prompt"].strip():
            ratio = policy["assets"]["character_ratio" if kind == "角色" else "scene_ratio"]
            if ratio not in asset["prompt"]:
                errors.append(f"{code}: 图片提示词缺少默认画幅 {ratio}")
            layout = "四视图" if kind == "角色" else "全景"
            if kind == "角色":
                # 一人一卡：角色资产图也可以是「场景内单张电影剧照」（视频参考形态），
                # 但必须显式写清，不能只靠「不是四视图」这种否定句蒙过版式检查。
                still = "单张" in asset["prompt"] and (
                    "剧照" in asset["prompt"] or "单人" in asset["prompt"])
                if not still and layout not in asset["prompt"]:
                    errors.append(
                        f"{code}: 图片提示词缺少默认{layout}版式，"
                        "也未声明一人一卡的单张剧照版式")
            elif layout not in asset["prompt"]:
                errors.append(f"{code}: 图片提示词缺少默认{layout}版式")
            if kind == "角色":
                _check_character_prompt_fields(asset, policy, warnings)
    # 一人一卡：同一角色的第二张卡（CHAR_0X_PHOTO 之类的后缀变体）在导入端会被当成
    # 新角色，典型后果是 5 人变 10 人、旧的孤儿卡删不掉。这里按「去掉后缀后同名」判重。
    _variant = re.compile(
        r"^(CHAR_\d+)_(PHOTO|STILL|VIEW|VIEWS|FRONT|SIDE|BACK|TURNAROUND)$", re.I)
    for code in list(codes):
        if codes[code] != "角色":
            continue
        m = _variant.match(code)
        if not m:
            continue
        if m.group(1) in codes:
            errors.append(
                f"{code}: 与 {m.group(1)} 是同一角色的第二张卡（{m.group(2)} 变体）——"
                "角色资产须一人一卡，导入端会把它当成新角色导致角色页重复；"
                "剧照形态请直接写进该角色的图片提示词")
        else:
            warnings.append(
                f"{code}: 角色代码带 {m.group(2)} 后缀，建议合并回 {m.group(1)}（一人一卡）")
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
                                      asset_codes=set(codes),
                                      asset_prompts=asset_prompts,
                                      extra_fields={k: v for k, v in shot["prompts"].items()
                                                    if k != "视频提示词"}))
    outfit_stats = check_outfit_consistency(parsed, char_names, errors, warnings)
    space_stats = {"status": "skipped"}
    if space_dir is not None:
        space_errors, space_warnings, space_stats = check_space_sync(
            parsed, char_names, Path(space_dir), model=model)
        errors.extend(space_errors)
        warnings.extend(space_warnings)
    if space_stats.get("status") != "checked":
        risky = risk_shot_count(parsed, char_names)
        space_stats["risk_shots"] = risky
        if risky and not space_exempt:
            errors.append(
                f"站位层缺失：本包含 {risky} 个多人同框镜头（命中风险闸门），但未找到可用的"
                f"站位增量（{space_dir or '内部/04b-站位图'}）；W18 要求在阶段 2 出场景基底、"
                f"阶段 3 出镜级增量后再编译正文。如确不建，须在 内部/00-项目输入单.md 登记"
                f"「站位层：豁免（理由：…）」")
        elif space_exempt:
            extra = f"（本包 {risky} 个多人同框镜头）" if risky else ""
            warnings.append(f"站位层：已按输入单登记豁免，跳过站位交叉校验{extra}")
    return {"ok": not errors, "episodes": len(episodes), "segments": len(stats),
            "assets": len(assets), "import_request_bytes": request_bytes,
            "stats": stats, "space": space_stats, "outfit": outfit_stats,
            "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验可导入的短剧精简制作包 Markdown")
    parser.add_argument("file", type=Path, help="已填写的精简制作包 Markdown 文件")
    parser.add_argument("--model", choices=["seedance25", "wan30", "h3"],
                        default="seedance25",
                        help="生成模型轨：seedance25（默认，整数秒/分档字数）、"
                             "wan30（0.5秒粒度/20000字符/2-30秒）、"
                             "h3（MiniMax H3 官方字段结构/app 默认30秒、official 4-15秒/毫秒切点）")
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
    parser.add_argument("--space-dir", type=Path, default=None,
                        help="站位增量目录（E28/W18）。缺省时按制作包同级 "
                             "内部/04b-站位图 自动查找；找不到则跳过站位交叉校验")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()
    try:
        source = args.file.read_text(encoding="utf-8")
        policy = json.loads((Path(__file__).resolve().parent.parent / "policy.json").read_text())
        baseline = None
        if args.sequel_baseline:
            baseline = args.sequel_baseline.read_text(encoding="utf-8")
        space_dir = args.space_dir
        if space_dir is None:
            candidate = args.file.resolve().parent
            for part in SPACE_DEFAULT_DIR:
                candidate = candidate / part
            space_dir = candidate
        result = validate(source, policy, model=args.model, tier=args.tier,
                          h3_segments=args.h3_segments, baseline=baseline,
                          space_dir=space_dir,
                          space_exempt=space_exempted(args.file))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"无法校验文件：{exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        space = result.get("space", {})
        outfit = result.get("outfit", {})
        print(f"精简制作包：{'通过' if result['ok'] else '失败'}；"
              f"{result['episodes']} 集、{result['segments']} 片段、{result['assets']} 项资产"
              + ("（续集校验）" if args.sequel_baseline else "")
              + (f"；服装变体：{outfit.get('outfit_assets', 0)} 件 / "
                 f"{outfit.get('outfit_bound', 0)} 处绑定"
                 if outfit.get("outfit_assets") else "")
              + (f"；站位交叉校验：{space.get('status')}"
                 f"（{space.get('fragments', 0)} 片段 / {space.get('overlays', 0)} 增量）"
                 if space.get("status") == "checked" else "；站位交叉校验：未启用"))
        for item in result["errors"]:
            print(f"  错误：{item}")
        for item in result.get("warnings", []):
            print(f"  提醒：{item}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
