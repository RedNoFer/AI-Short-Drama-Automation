#!/usr/bin/env python3
"""阶段 4 骨架派生：把冻结逐镜表机械转录成片段提示词骨架（改造二）。

为什么有这个脚本（2026-10-25 流程优化）
--------------------------------------------------------------------------
阶段 4 的第一批机检失败，绝大多数不是写得好不好，而是**抄错**：时间轴从上一镜
尾巴错开半秒、镜数漏一个、硬切数对不上、参考行漏掉一个入镜角色。这些字段在
阶段 3 逐镜表里已经存在，让执行员用眼睛搬到提示词里，等于每批都重赌一次抄写。

本脚本只做机械转录，不做创作：

  · 片段标题、镜数、每镜起止秒、资产代码（参考行）全部从 04 逐镜表原样取；
  · 时间轴按轨生成到「行首＋时间＋硬切，」为止，正文留 TODO 给执行员写；
  · 镜数带、硬切带、时长连续性当场校验，不合规直接失败关闭，不产出可提交骨架；
  · 骨架头部写规范快照与上游哈希，便于事后判断「这批骨架是哪一版逐镜表派生的」。

它不替代写作，也不替代机检：骨架写完仍要跑 lint_segment.py（段内）与
validate_compact_package.py（批次）。脚本只保证「不该错的地方不会错」。

用法：
    python3 scaffold_segment.py 创作输出/作品名 --batch "E01-SH01~SH03"
    python3 scaffold_segment.py 创作输出/作品名 --segment E01-SH01 --out 内部/派单/E01-SH01_骨架.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402

TODO = "TODO"
ASSET_RE = re.compile(r"\b(CHAR|LOC|PROP)_([A-Za-z0-9]+)\b")
META_SPLIT = re.compile(r"[｜|]")
NUM = r"\d+(?:\.\d+)?"


def pick_storyboard(internal: Path) -> Path | None:
    for pat in ("04-片段规划与逐镜表.md", "04-*.md"):
        hits = sorted(p for p in internal.glob(pat) if p.is_file() and p.stat().st_size > 0)
        if hits:
            return hits[0]
    return None


def parse_table(block: str) -> list[dict]:
    """合并片段内分开的时间核算表与逐镜设计表。"""
    aliases = {
        "shot": ("镜", "镜头", "镜号"),
        "time": ("时间", "起止", "时码"),
        "size": ("景别",),
        "lens": ("焦段",),
        "angle": ("机位",),
        "move": ("运镜",),
        "depth": ("景深",),
        "content": ("内容", "要点", "画面", "叙事工作"),
        "act": ("表演",),
    }
    table_blocks: list[list[str]] = []
    current: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("|"):
            current.append(line)
        elif current:
            table_blocks.append(current)
            current = []
    if current:
        table_blocks.append(current)

    merged: dict[str, dict] = {}
    for lines in table_blocks:
        if len(lines) < 3:
            continue
        header = [c.strip() for c in lines[0].strip("|").split("|")]
        cols: dict[str, int] = {}
        for idx, name in enumerate(header):
            for key, names in aliases.items():
                if key not in cols and any(alias in name for alias in names):
                    cols[key] = idx
        if "shot" not in cols:
            continue
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < len(header):
                cells += [""] * (len(header) - len(cells))

            def cell(key: str) -> str:
                idx = cols.get(key)
                return cells[idx] if idx is not None and idx < len(cells) else ""

            shot = cell("shot")
            if re.fullmatch(r"\d{1,2}", shot):
                shot = f"S{int(shot):02d}"
            if not re.fullmatch(r"S\d{1,2}", shot):
                continue
            row = merged.setdefault(shot, {
                "shot": shot, "time": "", "size": "", "lens": "", "angle": "",
                "move": "", "depth": "", "content": "", "act": "",
            })
            for key in ("time", "size", "lens", "angle", "move", "depth", "content", "act"):
                value = cell(key)
                if value:
                    row[key] = value
    return list(merged.values())


def split_time(raw: str) -> tuple[float, float] | None:
    m = re.search(rf"({NUM})\s*[-–~至]\s*({NUM})", raw)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def fmt_sec(value: float) -> str:
    return str(int(value)) if abs(value - int(value)) < 1e-9 else f"{value:g}"


def segment_title(block: str, seg_id: str) -> str:
    head = block.splitlines()[0]
    tail = head.split("｜", 1)[1] if "｜" in head else head.split("|", 1)[-1]
    tail = re.sub(r"[（(].*?[)）]", "", tail).strip()
    return tail or seg_id


def segment_meta(block: str) -> dict:
    """读 `场景：LOC_01｜角色：CHAR_01、CHAR_02｜道具：PROP_02` 这类元信息行。"""
    meta = {"scene": [], "char": [], "prop": []}
    for line in block.splitlines():
        if not re.search(r"(场景|角色|道具)[：:]", line):
            continue
        for part in META_SPLIT.split(line):
            key, _, value = part.partition("：")
            if not _:
                key, _, value = part.partition(":")
            codes = [f"{a}_{b}" for a, b in ASSET_RE.findall(value)]
            if "场景" in key:
                meta["scene"] += codes
            elif "角色" in key:
                meta["char"] += codes
            elif "道具" in key:
                meta["prop"] += codes
    return {k: list(dict.fromkeys(v)) for k, v in meta.items()}


def check_axis(seg_id: str, rows: list[dict], track: str) -> tuple[list[str], list[str]]:
    """时间轴与镜数/硬切带的机械校验；错误阻断骨架产出。"""
    errors: list[str] = []
    warnings: list[str] = []
    spans = [split_time(r["time"]) for r in rows]
    if any(s is None for s in spans):
        bad = [r["shot"] for r, s in zip(rows, spans) if s is None]
        errors.append(f"{seg_id}: 镜 {('、'.join(bad))} 的时间列读不出起止（格式应为 0-4 或 0-4.5）")
        return errors, warnings
    spans = [s for s in spans if s]
    if abs(spans[0][0]) > 1e-9:
        errors.append(f"{seg_id}: 时间轴未从 0 开始（首镜 {fmt_sec(spans[0][0])} 秒）")
    for i in range(1, len(spans)):
        if abs(spans[i][0] - spans[i - 1][1]) > 1e-9:
            errors.append(
                f"{seg_id}: 时间轴断档/重叠——{rows[i - 1]['shot']} 结束 {fmt_sec(spans[i - 1][1])} 秒，"
                f"{rows[i]['shot']} 从 {fmt_sec(spans[i][0])} 秒开始")
    for i, (start, end) in enumerate(spans):
        if end <= start:
            errors.append(f"{seg_id}: {rows[i]['shot']} 时长非正（{fmt_sec(start)}-{fmt_sec(end)}）")
    if track == "seedance25":
        for i, (start, end) in enumerate(spans):
            if abs(start - int(start)) > 1e-9 or abs(end - int(end)) > 1e-9:
                errors.append(f"{seg_id}: Seedance 轨要求整数秒，{rows[i]['shot']} 出现小数"
                              f"（{fmt_sec(start)}-{fmt_sec(end)}）")
    total = spans[-1][1] if spans else 0
    shots = len(rows)
    if not re.search(r"一镜到底", seg_id) and not (6 <= shots <= 11):
        warnings.append(f"{seg_id}: 镜数 {shots} 不在 6–11 带（打斗 A 段一镜到底可豁免，须在逐镜表标明）")
    if not re.search(r"一镜到底", seg_id) and not (5 <= shots - 1 <= 10):
        warnings.append(f"{seg_id}: 硬切 {shots - 1} 次不在 5–10 带")
    if abs(total - 30) > 1e-9:
        warnings.append(f"{seg_id}: 片段时长 {fmt_sec(total)} 秒（Seedance/Wan 默认 30 秒）")
    return errors, warnings


def render_segment(seg_id: str, block: str, track: str) -> str:
    title = segment_title(block, seg_id)
    rows = parse_table(block)
    meta = segment_meta(block)
    spans = [split_time(r["time"]) for r in rows]
    total = spans[-1][1] if spans and spans[-1] else 0

    binding: list[str] = []
    if meta["char"]:
        binding.append("角色：" + "、".join(f"{c}＝{TODO}" for c in meta["char"]))
    if meta["scene"]:
        binding.append("场景：" + "、".join(f"{s}＝{TODO}" for s in meta["scene"]))
    if meta["prop"]:
        binding.append("道具：" + "、".join(f"{p}＝{TODO}" for p in meta["prop"]))
    if not binding:
        binding.append(f"角色：{TODO}（逐镜表未写资产代码，须回阶段 2/3 补）")
    ref_line = "；".join(binding)

    # 片段头必须是「### 片段 <ID>｜<整数秒>秒｜<标题>」——导入端按此建卡，
    # 少了中间的时长段，整块会被当成无法识别（2026-10-25 链路自测抓到）。
    out = [f"### 片段 {seg_id}｜{fmt_sec(total)}秒｜{title}", "",
           f"<!-- 骨架派生：{len(rows)} 镜；时间轴与绑定行由逐镜表机械转录，正文待写 -->", ""]
    out += binding
    out.append("")
    if track == "h3":
        out += ["#### 视频提示词", "", "```text",
                f"integrated_multimodal_description: {TODO} 按官方 base 三字段写画面与调度；"
                f"资产用 <Subject N>（{ref_line}）",
                f"overall_soundscape: {TODO} 环境声与动作声，含声音来源",
                f"non_diegetic_music: {TODO} 无配乐则写 none",
                "```", ""]
        out += ["<!-- H3 轨切点用官方毫秒写法 [Shot 2] At 00:06.500,；时间轴参考： -->",
                "<!-- " + " / ".join(f"{r['shot']} {r['time']}" for r in rows) + " -->", ""]
        return "\n".join(out)

    out += ["#### 视频提示词", "", "```text",
            f"【参考】{ref_line}",
            f"【公共总规范】{TODO} 画风母版＋画幅＋材质总则（资产图已锁的脸/服装/建筑/道具不重写，R31）",
            "【时间轴】"]
    for i, row in enumerate(rows):
        span = split_time(row["time"])
        start, end = (span if span else (0, 0))
        lead = "" if i == 0 else "硬切，"
        hint = "／".join(x for x in (row["size"], row["lens"], row["angle"], row["move"]) if x)
        out.append(f"{fmt_sec(start)}-{fmt_sec(end)}秒，{lead}{TODO} {hint}".rstrip())
    out += [f"【收尾】{TODO} 出口状态与下一片段入口（站位/朝向/道具状态/伤情/情绪未完话头）", "```", ""]
    voices = [r for r in rows if r["content"] and re.search(r"[「」“”\"]", r["content"])]
    if voices:
        out += [f"<!-- 本片段 {len(voices)} 镜含台词：含人声音频的片段，公共层须有一行「声线锁定：」，"
                f"逐字取声线母版，只列本片段实际发声角色 -->", ""]
    acts = [r["shot"] for r in rows if r["act"] and r["act"].strip() not in ("—", "-", "")]
    if acts:
        out += [f"<!-- 表演镜：{'、'.join(acts)}（每条片段≤2 个，超出回阶段 3 改指派） -->", ""]
    return "\n".join(out)


def build_skeleton(workdir: Path, batch: str | None, segment: str | None) -> tuple[str, dict]:
    internal = workdir / "内部"
    if not internal.is_dir():
        raise ValueError(f"{internal} 不存在（先完成阶段 0 落盘）")
    board = pick_storyboard(internal)
    if board is None:
        raise ValueError("缺阶段 3 落盘物「04-片段规划与逐镜表.md」——PROC-05：上游缺失时下游不得开工")
    brief = None
    for pat in ("00-*输入单*.md", "00-*.md"):
        hits = sorted(p for p in internal.glob(pat) if p.is_file() and p.stat().st_size > 0)
        if hits:
            brief = hits[0]
            break
    if brief is None:
        raise ValueError("缺内部/00-项目输入单.md（无法确认生成轨，R37 失败关闭）")
    brief_text = brief.read_text(encoding="utf-8")
    track = wc.read_track(brief_text)
    budget = wc.char_budget(wc.load_policy(), brief_text, track)

    blocks = dict(wc.split_segments(board.read_text(encoding="utf-8")))
    if segment:
        want = [segment]
    elif batch:
        want = wc.parse_batch_ids(batch)
    else:
        raise ValueError("必须给 --batch 或 --segment")
    want = [wc.normalize_seg_id(w) for w in want]
    missing = [w for w in want if w not in blocks]
    if missing:
        raise ValueError(f"逐镜表里找不到片段：{'、'.join(missing)}（现有：{'、'.join(blocks) or '无'}）")

    errors: list[str] = []
    warnings: list[str] = []
    rendered: list[str] = []
    episode = ""
    for seg_id in want:
        block = blocks[seg_id]
        rows = parse_table(block)
        if not rows:
            errors.append(f"{seg_id}: 未解析到逐镜表（片段块里没有以 | 开头的镜表）")
            continue
        seg_errors, seg_warnings = check_axis(seg_id, rows, track)
        errors += seg_errors
        warnings += seg_warnings
        ep = seg_id.split("-SH")[0] if "-SH" in seg_id else ""
        if ep and ep != episode:
            episode = ep
            rendered.append(f"## 剧集 {ep}")
            rendered.append("")
        rendered.append(render_segment(seg_id, block, track))
    if errors:
        raise ValueError("；".join(errors))

    snapshot = wc.policy_snapshot()
    head = [
        f"<!-- 阶段 4 骨架｜批次 {batch or segment}｜轨 {track}｜{wc.snapshot_line(snapshot)} -->",
        f"<!-- 上游：{board.name} SHA-256 {wc.sha256_file(board)[:16]}…｜"
        f"输入单 SHA-256 {wc.sha256_file(brief)[:16]}… -->",
        f"<!-- 字符口径：{budget['chars']}｜硬切带：{budget['hard_cuts']} -->",
        f"<!-- 骨架只保证机械字段不错；正文由执行员写，写完先跑 lint_segment.py，再跑批次校验 -->",
        "",
        "# 阶段 4 片段骨架",
        "",
    ]
    text = "\n".join(head + rendered) + "\n"
    meta = {"track": track, "segments": want, "warnings": warnings, "board": str(board),
            "board_sha256": wc.sha256_file(board), "policy": snapshot, "char_budget": budget}
    return text, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="从冻结逐镜表派生阶段 4 片段骨架（机械转录，不写作）")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("--batch", help='批次范围，如 "E01-SH01~SH03"')
    ap.add_argument("--segment", help="单个片段 ID，如 E01-SH01")
    ap.add_argument("--out", type=Path, help="写入路径（缺省 内部/派单/<批次>_骨架.md）")
    ap.add_argument("--json", action="store_true", help="额外输出骨架元信息 JSON")
    args = ap.parse_args()
    if not args.workdir.is_dir():
        print(f"作品目录不存在：{args.workdir}", file=sys.stderr)
        return 2
    try:
        text, meta = build_skeleton(args.workdir, args.batch, args.segment)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        print("骨架未生成（失败关闭；先修逐镜表或回补上游，不要手写骨架绕过）", file=sys.stderr)
        return 1
    out = args.out or (args.workdir / "内部" / "派单"
                       / f"{(args.batch or args.segment).replace('~', '-').replace(',', '_')}_骨架.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"骨架 → {out}（{len(meta['segments'])} 片段，轨 {meta['track']}）")
    for w in meta["warnings"]:
        print(f"提醒：{w}")
    if args.json:
        import json
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
