#!/usr/bin/env python3
"""派单／骨架／台账／衔接检查共用的口径层（改造六：规范快照＋规则引用）。

为什么要有这个文件（2026-10-25 流程优化）
--------------------------------------------------------------------------
此前「生成轨怎么读、字符档取哪个、规范是哪一版」这三件事在多个脚本里各写一遍。
任何一处改了口径，其余几处不会跟着变——这就是「参数不一致」的结构性来源，也是
总控抄写错误的温床。本模块把这些口径收成唯一实现：

  · 生成轨：只从输入单唯一登记值读取，缺失/重复/无效一律抛错（R37 失败关闭）；
  · 字符档：只从登记轨的 policy profile 读取，禁止跨轨回退（Wan/H3 不吃 Seedance 档）；
  · 规范快照：policy 版本＋SHA-256，写进派单卡/骨架/台账，用于事后判定「这批评的是哪一版规范」。

用法（其余脚本统一从本模块 import，不各自实现）：
    from workflow_common import load_policy, policy_snapshot, read_track, char_budget
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
POLICY_PATH = SKILL / "policy.json"

TRACKS = ("seedance25", "wan30", "h3")
TRACK_ALIASES = {
    "seedance25": "seedance25", "seedance 2.5": "seedance25", "seedance2.5": "seedance25",
    "seedance": "seedance25",
    "wan30": "wan30", "wan3.0": "wan30", "wan 3.0": "wan30", "wan": "wan30",
    "h3": "h3", "minimaxh3": "h3", "minimax h3": "h3", "海螺h3": "h3", "海螺 h3": "h3",
}
# 输入单里允许的生成轨行名：生成轨 / 生成模型轨 / 生成模型（存量项目写法）。
# 不锚行尾：既有输入单常带第三、第四列（用户指定、备注），锚尾会把它们读丢。
TRACK_ROW = re.compile(
    r"^\|\s*(?:目标)?生成(?:模型轨|轨|模型)\s*\|([^|\n]*)", re.M)
TIER_RE = re.compile(r"\b(tier[123]_[A-Za-z0-9_]+)\b")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def markdown_headings(text: str) -> list:
    """Find actual Markdown headings, preserving offsets and ignoring fenced examples."""
    pattern = re.compile(r"^(#{1,6})[ \t]+([^\n]+)$", re.M)
    headings, offset, fence = [], 0, None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if marker:
            token, tail = marker.groups()
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not tail.strip():
                fence = None
        elif fence is None:
            heading = pattern.match(text, offset)
            if heading:
                headings.append(heading)
        offset += len(line)
    return headings


def markdown_section(text: str, label: str) -> str:
    """Read a heading and its descendants, ending at the next peer or ancestor."""
    headings = markdown_headings(text)
    for i, match in enumerate(headings):
        if label not in match.group(2):
            continue
        level = len(match.group(1))
        end = next((later.start() for later in headings[i + 1:]
                    if len(later.group(1)) <= level), len(text))
        return text[match.end():end]
    return ""


def review_rows(text: str) -> dict[str, list[dict]]:
    """Read current acceptance rows; prose references and fenced examples are not rows."""
    rows: dict[str, list[dict]] = {}
    fence = None
    for line_number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, tail = marker.groups()
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not tail.strip():
                fence = None
            continue
        if fence or not line.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`* ") for cell in line.strip().strip("|").split("|")]
        ids = [normalize_seg_id(cell.removeprefix("片段 ")) for cell in cells
               if re.fullmatch(r"(?:片段 )?[A-Za-z0-9_]+[-/]SH\d+", cell)]
        digests = [(i, cell.lower()) for i, cell in enumerate(cells)
                   if re.fullmatch(r"[a-fA-F0-9]{64}", cell)]
        if len(ids) != 1 or len(digests) != 1:
            continue
        digest_index, digest = digests[0]
        verdict = cells[digest_index + 1] if digest_index + 1 < len(cells) else ""
        verdict = re.sub(r"^结论\s*[：:]\s*", "", verdict)
        rows.setdefault(ids[0], []).append({
            "sha256": digest, "verdict": verdict, "line": line_number,
        })
    return rows


def review_row_errors(text: str, expected: dict[str, str]) -> list[str]:
    """Each expected segment needs one current row, a matching digest and a pass verdict."""
    rows = review_rows(text)
    errors = []
    for sid, digest in expected.items():
        records = rows.get(normalize_seg_id(sid), [])
        if not records:
            errors.append(f"阶段 4 评审未覆盖片段 {sid} 的当前验收表行")
            continue
        if len(records) != 1:
            errors.append(f"阶段 4 片段 {sid} 当前验收表行重复或结论冲突，必须唯一")
            continue
        record = records[0]
        if record["sha256"] != digest:
            errors.append(f"阶段 4 评审未列出片段 {sid} 当前提示词正文 SHA-256")
        if record["verdict"] != "通过":
            errors.append(f"阶段 4 片段 {sid} 逐条结论不是明确的通过：{record['verdict'] or '缺失'}")
    return errors


def review_scope_snapshot(text: str, segments: list[str]) -> dict | None:
    """Lock this batch's evidence plus shared constraints, excluding other segment sections.

    Flat legacy reports retain their whole-file lock. Aggregate verdict/count lines
    are checked by the full stage gate, so updating those alone does not reopen peers.
    """
    requested = {normalize_seg_id(sid) for sid in segments}
    if not requested:
        return None
    headings = markdown_headings(text)
    sections: dict[str, list[tuple[int, int]]] = {}
    for i, match in enumerate(headings):
        sid_match = re.match(r"^(?:片段[ \t]+)?([A-Za-z0-9_]+[-/]SH\d+)(?:[ \t｜|]|$)", match.group(2))
        if not sid_match:
            continue
        end = next((later.start() for later in headings[i + 1:]
                    if len(later.group(1)) <= len(match.group(1))), len(text))
        sections.setdefault(normalize_seg_id(sid_match[1]), []).append((match.start(), end))
    if not sections:
        return None
    if not requested.issubset(sections):
        raise ValueError(f"评审报告缺少本批片段分节：{'、'.join(sorted(requested - sections.keys()))}")
    spans = sorted(span for parts in sections.values() for span in parts)
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError("片段评审分节互相嵌套，无法安全锁定本批范围")
    local = {}
    for sid in sorted(requested):
        if len(sections[sid]) != 1:
            raise ValueError(f"片段 {sid} 评审分节重复")
        start, end = sections[sid][0]
        section = text[start:end].strip()
        rows = review_rows(section)
        records = rows.get(sid, [])
        if len(records) != 1 or records[0]["verdict"] != "通过":
            raise ValueError(f"片段 {sid} 必须有唯一且明确通过的当前验收表行")
        if set(rows) != {sid}:
            raise ValueError(f"片段 {sid} 分节混入其他片段的当前验收表行")
        local[sid] = sha256_text(section)
    shared = []
    cursor = 0
    for start, end in spans:
        shared.append(text[cursor:start])
        cursor = end
    shared.append(text[cursor:])
    aggregate = re.compile(
        r"^[ \t]*(?:[-*][ \t]*)?(?:(?:总体|整体|总评|评审)[ \t]*)?结论[ \t]*[：:][ \t]*(?:通过|需修改|未通过|待评)[。.]?[ \t]*$"
        r"|^[ \t]*(?:[-*][ \t]*)?未关闭阻断/重要缺陷[ \t]*[：:][ \t]*\d+[ \t]*$")
    shared_text = "\n".join(line for line in "".join(shared).splitlines() if not aggregate.fullmatch(line))
    return {"schema": "review-scope/1", "segments": local,
            "global_sha256": sha256_text(shared_text.strip())}


def stage_gate_inputs(workdir: Path, stage: str) -> dict[str, str]:
    """返回阶段门依赖文件哈希；排除后续提示词草稿，支持阶段门收据复用。"""
    internal = Path(workdir) / "内部"
    patterns = ["00-*.md", "01-*.md", "01c-*.md", "02-*.md", "02a-*.json",
                "03-*.md", "03b-*.md"]
    if stage in {"3", "3.5"}:
        patterns.append("04-*.md")
        patterns.append("04c-衔接事实.json")
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(p for p in internal.glob(pattern) if p.is_file())
    space = internal / "04b-站位图"
    if stage == "2" and space.is_dir():
        paths.update(p for p in space.glob("SCENE_*.json") if p.is_file())
    elif stage in {"3", "3.5"} and space.is_dir():
        paths.update(p for p in space.rglob("*") if p.is_file())
    if stage == "3.5":
        paths.update(p for p in internal.glob("04b-*打斗*.md") if p.is_file())
        paths.update(p for p in internal.glob("04b-*路由*.md") if p.is_file())
    result = {str(p.relative_to(workdir)): sha256_file(p) for p in sorted(paths)}
    result["@policy.json"] = sha256_file(POLICY_PATH)
    return result


def continuity_scope_snapshot(path: Path, segments: list[str]) -> dict:
    """Hash batch facts plus immediate neighbours; unrelated facts stay reusable."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("segments")
    if data.get("schema") != "continuity-facts/2" or not isinstance(rows, list):
        raise ValueError("衔接事实需为完整 continuity-facts/2")
    ids = [normalize_seg_id(str(row.get("id", ""))) for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or len(ids) != len(set(ids)):
        raise ValueError("衔接事实片段 ID 缺失、重复或结构无效")
    wanted = {normalize_seg_id(s) for s in segments}
    if not wanted.issubset(ids):
        raise ValueError("衔接事实缺本批片段：" + "、".join(sorted(wanted - set(ids))))
    indices = {i for i, sid in enumerate(ids) if sid in wanted}
    scoped = {j for i in indices for j in (i - 1, i, i + 1) if 0 <= j < len(rows)}
    return {ids[i]: sha256_text(json.dumps(rows[i], ensure_ascii=False, sort_keys=True))
            for i in sorted(scoped)}


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def recommended_batch_size(policy: dict, track: str) -> list[int]:
    """Scheduling guidance only; never changes the project's segment boundaries."""
    band = policy.get("execution", {}).get("batch_size_by_track", {}).get(track)
    if (not isinstance(band, list) or len(band) != 2
            or not all(isinstance(value, int) and value > 0 for value in band)
            or band[0] > band[1]):
        raise ValueError(f"policy.execution.batch_size_by_track.{track} 缺少有效的批次建议范围")
    return list(band)


def policy_snapshot(policy: dict | None = None) -> dict:
    """规范快照：这一批评的是哪一版规范。写进派单卡、骨架、台账三处。"""
    policy = policy or load_policy()
    return {
        "policy_version": policy.get("policy_version"),
        "policy_sha256": sha256_file(POLICY_PATH),
        "policy_path": str(POLICY_PATH),
    }


def snapshot_line(snapshot: dict) -> str:
    return (f"policy v{snapshot.get('policy_version', '?')}"
            f"（policy.json SHA-256 {str(snapshot.get('policy_sha256', ''))[:16]}…）")


def normalize_track(raw: str) -> str | None:
    """把输入单单元格归一成三条轨之一；含糊（同时出现两条轨）返回 None。

    先剥括号注释（`Wan3.0（--model wan30 轨…）` → `Wan3.0`）与强调符再精确比对，
    精确比对不中时才按整词扫描，且只接受唯一命中——`seedance20` 这类近似值必须
    判无效，不能被前缀匹配悄悄归到 Seedance 2.5。
    """
    cell = re.sub(r"[（(][^)）]*[)）]", "", raw).strip().strip("*").strip().lower()
    if cell in TRACK_ALIASES:
        return TRACK_ALIASES[cell]
    found = {track for alias, track in TRACK_ALIASES.items()
             if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", cell)}
    return found.pop() if len(found) == 1 else None


def read_track(brief_text: str) -> str:
    """读输入单的唯一生成轨。0 个或 ≥2 个都抛错，绝不静默回退默认轨（R37）。"""
    rows = [r.strip() for r in TRACK_ROW.findall(brief_text)]
    rows = [r for r in rows if r]
    if len(rows) != 1:
        raise ValueError(
            f"输入单的「生成轨」登记了 {len(rows)} 个值（必须且只能一个：seedance25｜wan30｜h3）")
    track = normalize_track(rows[0])
    if track is None:
        raise ValueError(f"输入单生成轨「{rows[0]}」无效（只接受 seedance25/wan30/h3）")
    return track


def char_budget(policy: dict, brief_text: str, track: str) -> dict:
    """字符与硬切口径只从登记轨的 profile 读取（R37：禁止跨轨回退）。"""
    if track == "seedance25":
        tier = TIER_RE.search(brief_text)
        tier_id = tier.group(1) if tier else policy.get("video", {}).get(
            "default_quality_tier", "tier2_xiaomo63")
        tiers = policy.get("video", {}).get("prompt_quality_tiers", {})
        if tier_id not in tiers:
            raise ValueError(f"输入单登记档位「{tier_id}」不在 policy.video.prompt_quality_tiers")
        t = tiers[tier_id]
        return {
            "track": track,
            "chars": f"≤{t['prompt_max_chars']} 字符（{t.get('label', tier_id)}）",
            "max_chars": t["prompt_max_chars"],
            "min_chars": None,
            "hard_cuts": t.get("hard_cuts", "5-10"),
            "tier": tier_id,
            "validator": "--model seedance25 --tier " + tier_id,
        }
    profile = policy.get("model_profiles", {}).get(track)
    if not profile or "prompt_max_chars" not in profile:
        raise ValueError(
            f"policy.json 缺 model_profiles.{track}.prompt_max_chars：长度策略缺失时失败关闭，不得回退其他轨")
    if track == "wan30":
        cap = profile["prompt_max_chars"]
        if type(cap) is not int or cap <= 0:
            raise ValueError("policy.json Wan3.0 prompt_max_chars 必须是正整数；不得回退其他轨")
        return {
            "track": track,
            "chars": f"仅硬顶 {cap} 字符，无字数下限、目标带或单拍字数配额；"
                     "按逐镜剧情、动作、运镜、情绪、表演、声音与衔接的清晰完整性评审，禁止注水",
            "max_chars": cap,
            "min_chars": None,
            "hard_cuts": "5-10（镜头 6-11；打斗 A 段一镜到底豁免，字符口径不变）",
            "tier": None,
            "validator": "--model wan30 ＋ audit_wan30_antipatterns.py（作者扫描只拦硬错；"
                         "阶段4全集用 --strict 与当前风险处置记录核对）",
        }
    return {
        "track": track,
        "chars": f"硬顶 {profile['prompt_max_chars']}、低于 {profile.get('prompt_min_chars', 1200)} 提醒过简；"
                 "不套 Seedance 档",
        "max_chars": profile["prompt_max_chars"],
        "min_chars": profile.get("prompt_min_chars", 1200),
        "hard_cuts": f"{profile.get('hard_cuts_min', 0)}-{profile.get('hard_cuts_max', 6)}",
        "tier": None,
        "validator": "--model h3" + (" --h3-segments official"
                                      if re.search(r"h3[-_ ]?segments\s*[=:：]\s*official", brief_text, re.I)
                                      else ""),
    }


def parse_batch_ids(batch: str) -> list:
    """解析批次范围：支持 "E03-SH01~SH04" 区间与逗号列表。"""
    ids: list[str] = []
    for part in batch.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "~" in part:
            left, right = (s.strip() for s in part.split("~", 1))
            m = re.match(r"^(.*?SH)(\d+)$", left)
            n = re.match(r"^(?:.*?SH)?(\d+)$", right)
            if m and n and int(n.group(1)) >= int(m.group(2)):
                prefix, a = m.group(1), int(m.group(2))
                ids.extend(f"{prefix}{k:02d}" for k in range(a, int(n.group(1)) + 1))
                continue
        ids.append(part)
    return ids


def batch_id(batch: str, brief_path: Path | None = None) -> str:
    raw = batch.replace("~", "-").replace(",", "_").replace("，", "_")
    if brief_path and Path(brief_path).is_file():
        return f"{raw}-{sha256_file(brief_path)[:8]}"
    return raw


# 片段标题的三种真实写法（同一批项目里并存，必须都认）：
#   ## E01_SH01｜扩音器响在大厅（30 秒 / 8 镜）      ← 逐镜表下划线形式
#   ## E01/SH01｜扩音器响在大厅（30 秒 / 8 镜）      ← 逐镜表斜杠形式
#   ## 一、片段 E01-SH01｜开场                       ← 逐镜表带序号
#   ### 片段 E01-SH01｜开场                          ← 精简制作包
SEGMENT_HDR = re.compile(
    r"^#{2,4}[ \t]*(?:[一二三四五六七八九十]+、)?[ \t]*(?:片段[ \t]*)?"
    r"([A-Za-z0-9]+[-_/]SH\d+)[ \t]*(?:｜|\||$)", re.M)


def normalize_seg_id(raw: str) -> str:
    """`E01_SH01`、`E01/SH01` 与 `E01-SH01` 统一成连字符。"""
    return raw.replace("／", "-").replace("/", "-").replace("_", "-").strip()


def split_segments(text: str) -> list[tuple[str, str]]:
    """按片段标题切块，返回 [(归一 ID, 块文本)]，保持原文顺序。"""
    blocks, markers = [], []
    episode = None
    for heading in markdown_headings(text):
        title = heading.group(2)
        ep = re.match(r"剧集[ \t]+([Ee]\d+)(?:[ \t｜|]|$)", title)
        if ep:
            episode = ep[1].upper()
        full = SEGMENT_HDR.match(text, heading.start())
        if full:
            markers.append((normalize_seg_id(full[1]), heading.start()))
            continue
        short = re.match(r"片段[ \t]+(SH\d+)(?:[ \t｜|]|$)", title)
        if short and episode:
            markers.append((f"{episode}-{short[1]}", heading.start()))
    for i, (sid, start) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(text)
        blocks.append((sid, text[start:end]))
    return blocks


def segment_ids(text: str) -> list[str]:
    return [sid for sid, _ in split_segments(text)]
