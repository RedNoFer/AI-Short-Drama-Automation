#!/usr/bin/env python3
"""单段即写即检：把一个片段抽进最小包骨架，立即跑登记轨校验器与 Wan 反例审计。

为什么有这个脚本（2026-10-25 流程优化）
--------------------------------------------------------------------------
此前的机检介入时点是「整批写完后装临时批次包」——一段一个小问题，付整批重检
成本；更晚则进入评审回滚，付快照修复＋重评审成本。本命令把检查压到「写完一段」
的当刻：上下文还热，命中即改一行，秒级重跑。

检查范围（重要）：
  · 段内项：四段结构、时间轴连续、硬切带、字符口径、程序性句式、声音标签、
    声线锁定行在位、Wan 反例词法（并肩/极缓慢/静物/空镜/不看镜头/暖光…）；
  · 跨段项**不在本命令范围**：声线锁定跨片一致（R4）、锚词全包同源（WAN30-09）、
    小说覆盖率（R7）、集间衔接——仍由批末临时包与交付门承担。执行员不得以
    「lint 过了」替代批次校验。Wan词法语义风险在本地显示为待评，只有硬错误
    阻断；阶段4全集审计使用 --strict 和当前版本逐项风险处置记录完成放行。

用法：
    python3 lint_segment.py 内部/派单/E03_草稿.md --segment E03-SH02
    python3 lint_segment.py 精简制作包.md --segment SH01 --model wan30

生成轨缺省从源文件旁的 内部/00-项目输入单.md 读取（R37：读不到即失败关闭，
不静默回退默认轨）。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402  轨道口径唯一实现
TRACK_ALIASES = {
    "seedance25": "seedance25", "seedance 2.5": "seedance25", "seedance2.5": "seedance25",
    "wan30": "wan30", "wan3.0": "wan30", "wan 3.0": "wan30",
    "h3": "h3", "minimaxh3": "h3", "minimax h3": "h3", "海螺h3": "h3", "海螺 h3": "h3",
}
TIER_RE = re.compile(r"\b(tier[123]_[A-Za-z0-9_]+)\b")
SEGMENT_HDR = re.compile(r"^### 片段\s+([A-Za-z0-9_]+-SH\d+|[A-Za-z0-9_]+)｜", re.M)
ASSET_HDR = re.compile(r"^## 固定资产\s*$", re.M)
SOURCE_ASSET_HDR = re.compile(
    r"^### (?:(角色|道具) )?(CHAR-\d+|PROP-\d+|SCENE_LOC_\d+)｜(.+)$", re.M)


def parse_sections(md: str) -> dict:
    """把包/草稿 MD 切成资产区、剧集区与逐片段块。"""
    segments: dict[str, str] = {}
    # 片段块的终点 = 下一个片段标题的绝对位置。旧实现把「相对 m.end() 的偏移」
    # 又加了一次绝对偏移（x.start() + m.end()），块会被截在句子中间，
    # 下游报「text 块缺少结束标记」——2026-10-25 串链路自测抓到。
    headers = list(SEGMENT_HDR.finditer(md))
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(md)
        segments[m.group(1)] = md[m.start():end]
    assets = ""
    a = ASSET_HDR.search(md)
    if a:
        nxt_ep = re.search(r"^## 剧集", md[a.end():], re.M)
        assets = md[a.start():a.end() + nxt_ep.start()] if nxt_ep else md[a.start():]
    return {"assets": assets, "segments": segments}


def find_segment(md: str, seg_id: str) -> str:
    sections = parse_sections(md)
    segs = sections["segments"]
    if seg_id in segs:
        return segs[seg_id]
    for key, block in segs.items():
        if key in seg_id or seg_id in key:
            return block
    raise ValueError(f"源文件里找不到片段「{seg_id}」（现有：{'、'.join(sorted(segs)) or '无'}）")


def detect_model(src: Path) -> tuple[str, str | None]:
    """从源文件旁的输入单读唯一生成轨；读不到即失败关闭（R37）。"""
    brief_text = find_brief(src)
    if not brief_text:
        raise ValueError("找不到源文件旁的 内部/00-项目输入单.md：无法确认登记轨，"
                         "请显式传 --model（seedance25｜wan30｜h3），或先把阶段 0 落盘")
    return parse_track(brief_text)


def find_brief(src: Path) -> str:
    # Drafts and skeletons live several levels below the project root. Walk upward
    # to the nearest real project input sheet; never mistake a sibling 00-*.md
    # note (for example a conflict log) for the unique generation-track record.
    for cand in (src.parent, *src.parents[1:]):
        hits = sorted((cand / "内部").glob("00-*输入单*.md")) if (cand / "内部").is_dir() else []
        hits += sorted(cand.glob("00-*输入单*.md"))
        if hits:
            return hits[0].read_text(encoding="utf-8")
    return ""


def find_project_root(src: Path) -> Path | None:
    """Find the project root whose input sheet and internal sidecars own ``src``."""
    for cand in (src.parent, *src.parents[1:]):
        if ((cand / "内部" / "00-项目输入单.md").is_file()
                or list((cand / "内部").glob("00-*输入单*.md"))):
            return cand
    return None


def find_default_asset_source(src: Path) -> Path | None:
    """Find the frozen Stage 2 asset prompts for a project-local draft."""
    project_root = find_project_root(src)
    if project_root is None:
        return None
    candidate = project_root / "内部" / "03a-固定资产图片提示词.md"
    return candidate if candidate.is_file() else None


def parse_track(brief_text: str) -> tuple[str, str | None]:
    track = wc.read_track(brief_text)
    tier = wc.TIER_RE.search(brief_text)
    return track, (tier.group(1) if track == "seedance25" and tier else None)


def build_mini_package(md: str, seg_id: str, assets_from: str = "") -> str:
    """拼 lint 最小包。骨架草稿本身没有资产区时，用 --assets 指向制作包补资产。"""
    block = find_segment(md, seg_id)
    assets = parse_sections(md)["assets"]
    if not assets and assets_from:
        assets = parse_sections(assets_from)["assets"]
        if not assets:
            # 阶段4派单的合法上游是阶段2原始资产提示词，不是尚未生成的最终包。
            # 将其临时映射为紧凑包资产区，才能逐段即写即检；不修改或复制到最终交付包。
            assets = source_asset_section(assets_from)
    if assets:
        # 单段 lint 只需本段绑定的资产；把其它资产也带入会让未使用场景/道具的
        # 缺项触发误报，并拖慢作者修正。最终整包校验仍会检查全部实际导入资产。
        used_codes = set(re.findall(r"\b(?:CHAR|LOC|PROP|CLUE)_[A-Za-z0-9_-]+\b", block))
        assets = filter_asset_section(assets, used_codes)
    if not assets:
        raise ValueError("源文件没有「## 固定资产」区：绑定校验会失真；"
                         "请对完整制作包或含资产区的草稿运行 lint_segment，"
                         "或用 --assets 指向含资产区的制作包（骨架草稿走这条）")
    novel = "```text\n（lint 最小包：本块仅满足结构，不参与覆盖率检查）\n```"
    # Keep the real E##/SH## identity so the compact validator can join this one
    # segment to its W18 overlays. The old E99 placeholder silently skipped the
    # project's space truth layer, because the temp package also lived in /tmp.
    header = SEGMENT_HDR.search(block)
    if not header:
        raise ValueError(f"片段「{seg_id}」缺少可识别的片段标题")
    full_code = header.group(1)
    explicit = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)-(SH\d+)", full_code)
    if explicit:
        episode_code, fragment_code = explicit.groups()
    else:
        fragment_code = full_code
        block_start = md.find(block)
        preceding = md[:block_start] if block_start >= 0 else ""
        episodes = list(re.finditer(r"(?m)^## 剧集 ([A-Za-z][A-Za-z0-9_-]*)｜", preceding))
        if not episodes:
            raise ValueError(f"无法从源文件上下文识别「{full_code}」所属剧集")
        episode_code = episodes[-1].group(1)
    normalized_block = re.sub(
        r"(?m)^### 片段 [A-Za-z0-9_]+(?:-SH\d+)?｜",
        f"### 片段 {fragment_code}｜", block, count=1)
    return ("# 精简制作包\n\n" + assets.rstrip() + "\n\n"
            f"## 剧集 {episode_code}｜lint-segment\n\n### 小说原文\n\n" + novel + "\n\n"
            + normalized_block.rstrip() + "\n")


def source_asset_section(source: str) -> str:
    """把阶段2的 CHAR-/PROP-/SCENE_LOC_ 资产提示词映射为 lint 可读的临时资产区。"""
    matches = list(SOURCE_ASSET_HDR.finditer(source))
    if not matches:
        return ""
    rows = ["## 固定资产"]
    kind_map = {"CHAR-": "角色", "PROP-": "道具", "SCENE_LOC_": "场景"}
    for index, match in enumerate(matches):
        raw_code, name = match.group(2), match.group(3).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        body = source[start:end].strip()
        # 拆掉资产卡的状态/用途标签，只把已写明的外观提示词作为临时 lint 资产正文。
        body = re.sub(r"(?m)^\*\*状态[^\n]*\*\*\s*\n?", "", body)
        body = re.sub(r"(?m)^\*\*状态：[^\n]*\*\*\s*\n?", "", body)
        body = re.sub(r"(?m)^#### 图片提示词\s*$\n?", "", body)
        body = re.sub(r"(?m)^产品图提示词：\s*", "", body)
        body = re.sub(r"(?m)^图片提示词：\s*", "", body)
        # 道具/场景章节之间有普通二级标题；它们不属于提示词，切掉后续说明文字。
        body = re.split(r"(?m)^## (?:三、|四、|五、)?(?:场景|道具|角色|资产).*$", body, maxsplit=1)[0].strip()
        # SCENE_LOC_06 in this project is a JSON/text space base, explicitly
        # not a generated empty-scene image. Do not invent a picture asset from
        # its explanatory note; segments must bind the actual PROP instead.
        if raw_code.startswith("SCENE_LOC_") and "不制作空镜图片" in body:
            continue
        # PROP-38 等源资产正文自带 text fence；外层资产块只保留一个统一 fence。
        if body.startswith("```text") and body.endswith("```"):
            body = body[len("```text"): -len("```")].strip()
        body = body.replace("```text", "").replace("```", "").strip()
        prefix = next((p for p in kind_map if raw_code.startswith(p)), None)
        if prefix is None:
            continue
        kind = kind_map[prefix]
        code = raw_code.replace("-", "_") if prefix != "SCENE_LOC_" else raw_code.replace("SCENE_LOC_", "LOC_")
        rows.extend([f"### {kind} {code}｜{name}", "#### 图片提示词", "```text", body,
                     "```", ""])
    return "\n".join(rows).rstrip() if len(rows) > 1 else ""


def filter_asset_section(section: str, codes: set[str]) -> str:
    """Keep only requested asset cards from a compact-form asset section."""
    headers = list(re.finditer(
        r"^### (?:角色|场景|道具|线索) ([A-Za-z][A-Za-z0-9_-]*)｜.+$", section, re.M))
    kept = ["## 固定资产"]
    for index, match in enumerate(headers):
        if match.group(1) not in codes:
            continue
        start = match.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(section)
        kept.append(section[start:end].strip())
    return "\n\n".join(kept)


def run(src: Path, seg_id: str, model: str | None, tier: str | None,
        assets: Path | None = None) -> int:
    md = src.read_text(encoding="utf-8")
    asset_source = assets
    if asset_source is None and not parse_sections(md)["assets"]:
        asset_source = find_default_asset_source(src)
    assets_text = asset_source.read_text(encoding="utf-8") if asset_source else ""
    mini = build_mini_package(md, seg_id, assets_text)
    with tempfile.TemporaryDirectory() as d:
        pkg = Path(d) / "lint_单段包.md"
        pkg.write_text(mini, encoding="utf-8")
        cmd = [sys.executable, str(SCRIPTS / "validate_compact_package.py"), str(pkg), "--model", model]
        project_root = find_project_root(src)
        if project_root:
            space_dir = project_root / "内部" / "04b-站位图"
            if space_dir.is_dir():
                cmd += ["--space-dir", str(space_dir)]
        if model == "seedance25" and tier:
            cmd += ["--tier", tier]
        checked = subprocess.run(cmd, capture_output=True, text=True)
        print(f"── lint_segment {seg_id}（轨：{model}{'／' + tier if tier else ''}）──")
        print(checked.stdout.strip() or checked.stderr.strip())
        rc = checked.returncode
        if model == "wan30":
            audited = subprocess.run(
                [sys.executable, str(SCRIPTS / "audit_wan30_antipatterns.py"), str(pkg)],
                capture_output=True, text=True)
            print("── Wan3.0 局部审计：硬错误阻断；语义风险待独立评审，未获阶段4验收 ──")
            print(audited.stdout.strip() or audited.stderr.strip())
            rc = max(rc, audited.returncode)
    print("── 范围提醒：本命令只查段内项；声线跨片一致、锚词全包同源、覆盖率与集间衔接仍由批次校验与交付门承担 ──")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="单段即写即检（段内项；跨段项仍归批次校验）")
    ap.add_argument("source", type=Path, help="含「### 片段」结构的包或草稿 MD")
    ap.add_argument("--segment", required=True, help="片段 ID（如 E03-SH02 或 SH02）")
    ap.add_argument("--model", choices=["seedance25", "wan30", "h3"], help="缺省从输入单登记轨读取")
    ap.add_argument("--assets", type=Path,
                    help="覆盖默认资产来源；项目内草稿默认读取内部/03a-固定资产图片提示词.md")
    args = ap.parse_args()
    src = args.source
    if not src.is_file():
        print(f"源文件不存在：{src}", file=sys.stderr)
        return 2
    try:
        if args.model:
            brief = find_brief(src)
            track, tier = parse_track(brief) if brief else (args.model, None)
            if track != args.model:
                print(f"错误：--model {args.model} 与输入单登记轨「{track}」不一致（R37 失败关闭）", file=sys.stderr)
                return 1
            model = track
        else:
            model, tier = detect_model(src)
        if args.assets and not args.assets.is_file():
            print(f"错误：--assets 指向的文件不存在：{args.assets}", file=sys.stderr)
            return 1
        return run(src, args.segment, model, tier, args.assets)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
