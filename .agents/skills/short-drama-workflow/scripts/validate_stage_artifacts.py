#!/usr/bin/env python3
"""阶段出口门：每个阶段的落盘物必须齐备且自洽，并保存可复核的版本收据。

用法：
    python3 validate_stage_artifacts.py <作品目录> --stage 2
    python3 validate_stage_artifacts.py <作品目录> --stage 3
    python3 validate_stage_artifacts.py <作品目录> --stage 3.5
    python3 validate_stage_artifacts.py <作品目录> --stage all

为什么有这道门（2026-10-22 事故复盘）
--------------------------------------------------------------------------
上一轮《三千国道》重制时，阶段 2/3 的站位层被整段跳过，而**流水线里没有任何一道
门会因为它缺席而失败**：

  · 阶段 2/3 的落盘清单（站位基底／镜级增量／继承表）没有任何校验器检查；
  · `validate_compact_package --space-dir` 曾是可选参数并可能跳过；当前命中风险闸门时会 fail closed，缺站位增量且无输入单豁免即报错；
  · 所有机检都只跑在最终交付包上，看不见上游阶段。

结果是 4 轮返工（约 50 路 agent），其中 3 轮返工的根因都是"阶段 2/3 该固化的东西
被推到了交付后"。本脚本把这些上游落盘物变成**带门的硬约束**。

2026-10-23 升级：门查结构，不查关键字
--------------------------------------------------------------------------
第一版门只查「声线母版」「视感自查」这些字有没有出现，于是**写个空标题、贴张空
表格就能过门**——这比"最后才审"更危险，因为它给的是"已过门"的假信号。现在：

  · 必登标题下必须有正文（空标题判错）；
  · 表格必须有数据行（空表格判错）；
  · 每个角色必须在角色美工账里各有一行（缺行判错）；
  · 持物链必须有箭头链或表格行；
  · 阶段 3 的「视感统计：」声明值必须与逐镜表实算值一致（crosscheck_storyboard）；
  · 阶段 3 的实际分镜片段 ID 必须完整覆盖 02a 计划，缺段/重复/计划外均判错；
  · 阶段 2 必须有隔离评稿人的 `内部/03b-资产评审.md`；
  · 阶段 3.5 打斗路由 A/B/C 判定必须有表，A 级须带拍点、一镜到底与原文证据。

判定口径
--------------------------------------------------------------------------
风险闸门（W18）：多人同框 ≥2 人／固定座位或排位／有前后排／狭小室内／
有操作位或设备承托／有人走位或离席。命中即必须建站位层。

站位层豁免：项目的 `内部/00-项目输入单.md` 写 `站位层：豁免（理由：…）` 才可跳过；
**默认必须建**。这是刻意设计成"默认要建、豁免要留痕"——反过来就等于默认可以不做。

其他豁免：`阶段门豁免：<条目>（理由：…）`，不写理由的豁免无效。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402
import batch_ledger as ledger  # noqa: E402
import validate_workflow_manifest as workflow_manifest  # noqa: E402
import continuity_facts as continuity  # noqa: E402

CHARS = ("阿泽", "苏晚", "老杨", "许棠", "小林", "黑衣人")
# 通用角色名（供其他项目用）：取资产区「角色」资产名的主名
ROW = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒[，,](.*)$", re.M)
SCENE_HDR = re.compile(r"场\s*\d+-\d+")
EXEMPT_RE = re.compile(r"站位层[：:]\s*豁免")
# 阶段门豁免（仅限旧版重制等确实无法回补的项，必须写理由；每项都按提醒报出）
STAGE_EXEMPT_RE = re.compile(r"阶段门豁免[：:]\s*(.+)$", re.M)
_POLICY_CACHE: dict | None = None


def _policy() -> dict:
    """读取项目策略（缺文件时降级为空字典，不阻断门本身）。"""
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        path = Path(__file__).resolve().parent.parent / "policy.json"
        try:
            _POLICY_CACHE = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _POLICY_CACHE = {}
    return _POLICY_CACHE


def _main_name(raw: str) -> str:
    """「阿泽（领队）」→「阿泽」，用于账目比对。"""
    return re.split(r"[（(]", raw or "")[0].strip()


def _load_crosscheck():
    """加载同目录的视感交叉校验模块（缺失即报错，不静默跳过）。"""
    import importlib.util

    path = Path(__file__).resolve().parent / "crosscheck_storyboard.py"
    if not path.is_file():
        raise RuntimeError(f"找不到 {path}")
    spec = importlib.util.spec_from_file_location("crosscheck_storyboard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_exemptions(workdir: Path) -> set:
    """读取输入单的「阶段门豁免：」条目，返回被豁免的关键词集合。"""
    internal = workdir / "内部"
    text = ""
    for pat in ("00-*输入单*.md", "00-*.md"):
        for f in sorted(internal.glob(pat)):
            text += f.read_text(encoding="utf-8")
    out = set()
    for m in STAGE_EXEMPT_RE.finditer(text):
        for token in re.split(r"[；;、,，]", m.group(1)):
            token = token.strip()
            if not token:
                continue
            # 没写理由的豁免无效（防止豁免变成新的跳步后门）
            if "（理由" not in token and "(理由" not in token:
                continue
            out.add(re.split(r"[（(]", token, maxsplit=1)[0].strip())
    return out


# ---------------------------------------------------------------- 工具

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def char_names(workdir: Path) -> list:
    """从交付包或资产卡里取角色名。"""
    names = set(CHARS)
    for path in list(workdir.glob("精简制作包*.md")) + list((workdir / "内部").glob("*.md")):
        text = _read(path)
        for m in re.finditer(r"### 角色 ([A-Za-z0-9_]+)｜([^（\n（]+)", text):
            name = m.group(2).strip()
            if name:
                names.add(name)
    return sorted(n for n in names if len(n) >= 2)


def risk_shots_from_text(text: str, names: list) -> set:
    """文本里画内 ≥2 人的时间行集合。"""
    hits = set()
    for m in ROW.finditer(text):
        body = m.group(3)
        if sum(1 for n in names if n in body) >= 2:
            hits.add(m.group(0)[:40])
    return hits


def risk_scenes_from_script(workdir: Path, names: list) -> set:
    """剧本里 ≥2 人同场的场次 → 风险场景（用场景名做键）。"""
    script = ""
    for name in ("02-逐集拍摄剧本.md", "01-故事档案与分集规划.md", "02-资产与空间设计.md"):
        script = _read(workdir / "内部" / name)
        if script:
            break
    scenes = set()
    headers = list(re.finditer(r"### 场景 ([A-Za-z0-9_]+)｜([^\n（]*)", script))
    for m in headers:
        code = m.group(1)
        block = script[m.end():m.end() + 1200]
        if sum(1 for n in names if n in block) >= 2:
            scenes.add(code)
    if not headers:
        # 无可解析的场景头（剧本格式不同）：无法判定，按场景全算风险（宁可多要基底）
        for m in re.finditer(r"### 场景 ([A-Za-z0-9_]+)｜", script):
            scenes.add(m.group(1))
    return scenes


# ---------------------------------------------------------------- 各阶段门

def _pick(internal: Path, patterns: list) -> Path | None:
    """按模式匹配落盘物（不同项目命名不同，不能硬编码文件名）。"""
    for pat in patterns:
        hits = sorted(internal.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None


# ---------------------------------------------------------------- 结构检查
#
# 2026-10-23 审计：阶段 2/3 的「必登内容」原来只查关键字是否出现，写一个空标题、
# 贴一张空表格就能过门。这比「最后才审」更危险——它给了「已过门」的假信号。
# 以下把关键字检查升级为结构检查：标题下必须有正文，表格必须有数据行。

HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
DIM_WORDS = ("站位", "朝向", "视线", "道具", "光向", "情绪", "轴线", "战损", "承接")


def _sections(text: str) -> list[tuple[str, str]]:
    """按 2–4 级标题切块，返回 [(标题, 正文)]，保持文件顺序。"""
    out: list[tuple[str, str]] = []
    title: str | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        match = HEADING.match(line)
        if match:
            if title is not None:
                out.append((title, "\n".join(buf)))
            title = match.group(2)
            buf = []
        elif title is not None:
            buf.append(line)
    if title is not None:
        out.append((title, "\n".join(buf)))
    return out


def _table_rows(body: str) -> list[list[str]]:
    """取 markdown 表格的数据行（跳过表头与 |---| 分隔行）。"""
    rows: list[list[str]] = []
    seen_header = False
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.fullmatch(r"\|[\s|:\-—]+\|?", stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not seen_header:
            seen_header = True
            continue
        if any(cells):
            rows.append(cells)
    return rows


def _find_section(text: str, aliases: tuple) -> tuple[str, str] | None:
    for title, body in _sections(text):
        if any(alias in title for alias in aliases):
            return title, body
    return None


def _require_section(errors: list, text: str, label: str, aliases: tuple, *,
                     min_chars: int = 30, min_rows: int = 0,
                     need_words: tuple = ()) -> str | None:
    """标题存在 + 正文非空 + 表格有数据行 + 关键维度词在场。返回该段正文。"""
    hit = _find_section(text, aliases)
    if hit is None:
        errors.append(f"{label} 缺必登内容「{aliases[0]}」")
        return None
    title, body = hit
    stripped = body.strip()
    if len(stripped) < min_chars:
        errors.append(f"{label}「{title}」是空标题（正文仅 {len(stripped)} 字符，至少需 {min_chars}）")
        return body
    if min_rows:
        rows = _table_rows(body)
        if len(rows) < min_rows:
            errors.append(f"{label}「{title}」表格只有 {len(rows)} 行数据（至少需 {min_rows} 行，空表格不算登记）")
    if need_words:
        missing = [w for w in need_words if w not in body]
        if len(missing) > len(need_words) - 3:
            errors.append(f"{label}「{title}」缺状态维度：{'、'.join(missing)}")
    return body


def _character_field_warnings(asset_text: str, policy: dict, warnings: list) -> None:
    """阶段 2 就报角色图片提示词的九块字段缺口（原来只在最终包上提醒）。

    只报「哪一块没写」，不判断写得好不好——细节质量仍由角色美工账与独立评审承担。
    """
    groups = policy.get("assets", {}).get("character_prompt_groups", {})
    if not groups:
        return
    blocks = re.split(r"^### 角色\s+([A-Za-z][A-Za-z0-9_-]*)｜(.+)$", asset_text, flags=re.M)
    for i in range(1, len(blocks) - 2, 3):
        code, name, body = blocks[i], _main_name(blocks[i + 1]), blocks[i + 2]
        missing = [label for label, words in groups.items()
                   if not any(word in body for word in words)]
        if missing:
            warnings.append(
                f"阶段2 {code}「{name}」角色图片提示词缺美工字段：{'；'.join(missing)}"
                "（素颜、无饰品也须写明；字段在场不等于写得好）")
        if "全身" not in body:
            warnings.append(
                f"阶段2 {code}「{name}」没写全身——半身卡锁不住下装与鞋，"
                "Wan3.0 轨按错误处理")
        if "裤" not in body and "裙" not in body:
            warnings.append(
                f"阶段2 {code}「{name}」没写下装（裤/裙）——成片里的裤裙会逐镜变")
        if "鞋" not in body and "靴" not in body:
            warnings.append(
                f"阶段2 {code}「{name}」没写鞋——成片里的鞋会逐镜变")


# 阶段2 必有的落盘物：语义名 → 可接受的命名模式（覆盖 0X- 两套模板命名）
STAGE2_ARTIFACTS = {
    "项目输入单": ["00-*输入单*.md", "00-*.md"],
    "故事/分集规划": ["01-*分集*.md", "01-*故事*.md", "01-*.md"],
    "剧本": ["02-*剧本*.md", "01-*剧本*.md", "02-逐集拍摄剧本.md"],
    "资产与空间设计": ["03-*资产*.md", "02-*资产*.md"],
}


def _scene_plate_table_warnings(asset_text: str, warnings: list) -> None:
    """阶段 2 场景资产表就要标清「场景图 0 人／空镜」，名称不得带可移动道具。

    最终包由 validate_compact_package 硬拦；这里提前提醒，避免资产卡阶段把
    人物或车辆写成场景固定物。
    """
    for line in asset_text.splitlines():
        if not re.match(r"\|\s*LOC_[A-Za-z0-9_]+\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[1] != "场景":
            continue
        code, name, last = cells[0], cells[2], cells[-1]
        if not re.search(r"0\s*人|空镜|无人物", last):
            warnings.append(
                f"阶段2 场景资产表 {code} 未标「场景图 0 人／空镜」："
                "场景图只做空镜底板，人物与车辆由片段绑定与 PROP 承载")
        vehicle = re.search(r"轿车|汽车|卡车|摩托|自行车|三轮车", name)
        if vehicle:
            warnings.append(
                f"阶段2 场景资产 {code} 名称含可移动道具「{vehicle.group(0)}」："
                "场景名去掉车辆，车辆另登记 PROP，否则模型会把车重新画进底图")


def stage2(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    found: dict[str, Path] = {}
    for label, patterns in STAGE2_ARTIFACTS.items():
        path = _pick(internal, patterns)
        if path is None:
            errors.append(f"阶段2 缺少落盘物「{label}」（查找模式 {' / '.join(patterns)}）")
        else:
            found[label] = path
    # 必登内容：声线母版 / 角色美工账 / 持物链（分散在资产类文件里，合并检查）
    asset_files = sorted(
        {h for pat in ("02-*.md", "03-*.md") for h in internal.glob(pat) if h.is_file()}
        | {found[k] for k in ("资产与空间设计",) if k in found}
    )
    asset_text = "\n".join(f.read_text(encoding="utf-8") for f in asset_files)
    for match in re.finditer(r"#### 图片提示词\s*\n\s*```text\n(.*?)\n```", asset_text, re.S):
        if re.search(r"资产来源[：:]|原图文件[：:]|(?:内部|创作输出)[/\\]|(?:不另|不再)(?:行)?生成|本剧\s*E\d", match.group(1)):
            errors.append("阶段2 图片提示词混入来源说明、本地路径或项目操作指令；必须改为供应商可执行绘图正文")
    exempt_items = stage_exemptions(workdir)

    def _content(label: str, aliases: tuple, **kw) -> None:
        if label in exempt_items:
            warnings.append(f"阶段2「{label}」已登记阶段门豁免，按缺口放行")
            return
        body = _require_section(errors, asset_text, "阶段2", aliases, **kw)
        if label == "角色美工账" and body:
            # 每个角色必须在美工账里有一行（只写在提示词里、账上没记＝未定版）
            names = [_main_name(m.group(1)) for m in
                     re.finditer(r"^### 角色\s+[A-Za-z][A-Za-z0-9_-]*｜(.+)$", asset_text, flags=re.M)]
            absent = [n for n in names if n and n not in body]
            if absent:
                errors.append(f"阶段2 角色美工账缺这些角色的行：{'、'.join(absent)}")

    _content("声线母版", ("声线母版", "声线锚点"), min_chars=40)
    _content("角色美工账", ("角色美工账", "美工账"), min_chars=30)
    _content("持物链", ("持物链", "持物表", "道具链"), min_chars=20)
    if "持物链" not in exempt_items:
        hit = _find_section(asset_text, ("持物链", "持物表", "道具链"))
        if hit and hit[1].strip() and "→" not in hit[1] and "->" not in hit[1] \
                and not _table_rows(hit[1]):
            errors.append("阶段2 持物链需逐道具一行（获取点→持有人变更→去向），"
                          "既无箭头链也无表格行视为未登记")

    # 阶段 2 独立评审：资产母版是全剧污染源，不能只靠生产方自检
    if "阶段2评审" in exempt_items or "资产评审" in exempt_items:
        warnings.append("阶段2 资产独立评审已登记阶段门豁免，按缺口放行")
    else:
        review = _pick(internal, ["03b-*评审*.md", "03b-*.md", "0[0-9]-*资产评审*.md"])
        if review is None:
            errors.append("阶段2 缺独立评审记录（内部/03b-资产评审.md）：资产母版与声线母版"
                          "须由与起草方隔离的评审子任务复核，不能只靠生产方自检")
        elif len(review.read_text(encoding="utf-8").strip()) < 60:
            errors.append(f"阶段2 独立评审记录「{review.name}」内容过短（<60 字符），视为未评审")
        else:
            review_text = review.read_text(encoding="utf-8")
            if not re.search(
                    r"^\s*(?:[-*]\s*)?(?:(?:总体|评审)\s*)?结论\s*[：:]\s*通过(?:\s*[，,。；;]|$)",
                    review_text, re.M):
                errors.append(f"阶段2 独立评审记录「{review.name}」没有明确的通过结论")
            if not re.search(r"未关闭阻断/重要缺陷\s*[：:]\s*0\b", review_text):
                errors.append(f"阶段2 独立评审记录「{review.name}」没有明确写「未关闭阻断/重要缺陷：0」")
            if not re.search(r"(评稿人|评审人|子任务|模型)", review_text):
                errors.append(f"阶段2 独立评审记录「{review.name}」没有标明独立评审人")
            layering = _find_section(review_text, ("分层与去重", "提示词分层"))
            if layering is None:
                warnings.append(
                    "阶段2 独立评审缺「分层与去重」段：资产图写全外观/空间/形制，"
                    "视频只写机位/动作/状态变化；同一事实不在两个资产或正文里重复（R31）")
            elif len(layering[1].strip()) < 20:
                warnings.append(
                    f"阶段2 独立评审「{layering[0]}」是空标题：须写资产图不写什么、"
                    "视频不重复什么，并给出证据（R31）")

    _character_field_warnings(asset_text, _policy(), warnings)
    _scene_plate_table_warnings(asset_text, warnings)
    # 站位层：风险场景必须各有基底
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    risk = risk_scenes_from_script(workdir, names)
    bases = sorted((internal / "04b-站位图").glob("SCENE_*.json")) if (internal / "04b-站位图").is_dir() else []
    if exempt:
        warnings.append("站位层：已按输入单登记豁免（阶段2 不要求场景基底）")
    elif risk:
        have = {b.stem.replace("SCENE_", "") for b in bases}
        missing = sorted(risk - have)
        if missing:
            exempt = stage_exemptions(workdir)
            pending = [m for m in missing if m not in exempt and "场景基底" not in exempt]
            if pending:
                errors.append(f"阶段2 站位层：风险场景缺场景基底 {pending}（命中闸门：多人同框/固定座位/前后排/狭小室内/操作位/走位）")
            else:
                warnings.append(f"阶段2 场景基底 {missing} 已登记豁免")
        for b in bases:
            try:
                doc = json.loads(b.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{b.name} JSON 解析失败：{exc}")
                continue
            for key in ("scene", "characters", "props", "camera", "lighting", "continuity"):
                if key not in doc:
                    errors.append(f"{b.name} 缺字段 {key}")
    return errors, warnings


def _space_cast_conflicts(board_text: str, overlay_paths: list[Path]) -> list[str]:
    """Catch explicit in-frame/off-screen conflicts between the frozen shot table and W18 overlays."""
    segment_to_c = {
        match.group(1): f"C{int(match.group(2)):02d}"
        for match in re.finditer(r"(?m)^## (E\d+_SH\d+)｜C(\d+)｜", board_text)
    }
    c_to_segment = {c: segment for segment, c in segment_to_c.items()}
    cast_by_shot: dict[tuple[str, str], str] = {}
    active = False
    cast_index = None
    for line in board_text.splitlines():
        if line.startswith("|") and ("画内人物" in line or "画面人物" in line):
            headers = [cell.strip() for cell in line.strip("|").split("|")]
            cast_index = next((i for i, cell in enumerate(headers)
                               if cell in {"画内人物", "画面人物"}), None)
            active = cast_index is not None
            continue
        if active and line.startswith("|---"):
            continue
        if active and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cast_index is None or len(cells) <= cast_index or len(cells) < 2:
                continue
            first, shot = cells[0], cells[1]
            if re.fullmatch(r"C\d+", first) and re.fullmatch(r"S\d+", shot):
                segment = c_to_segment.get(first)
                shot_id = shot
            elif re.fullmatch(r"E\d+_SH\d+", first) and re.fullmatch(r"\d+", shot):
                segment = first
                shot_id = f"S{int(shot):02d}"
            else:
                continue
            if segment:
                cast_by_shot[(segment, shot_id)] = cells[cast_index]
        else:
            active = False
            cast_index = None

    errors: list[str] = []
    for path in overlay_paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # The structural gate reports malformed/missing JSON separately.
        shot = str(doc.get("shot") or "")
        match = re.fullmatch(r"(E\d+_SH\d+)_S(\d+)", shot)
        if not match:
            continue
        segment, number = match.groups()
        cast = cast_by_shot.get((segment, f"S{int(number):02d}"))
        if cast is None:
            continue
        groups = [item.strip() for item in re.split(r"[；;]", cast) if item.strip()]
        for character in doc.get("characters") or []:
            if not isinstance(character, dict):
                continue
            name = str(character.get("name") or "")
            aliases = [re.split(r"[（(]", name, maxsplit=1)[0].strip()]
            suffix = re.search(r"[（(]([^）)]+)", name)
            if suffix:
                aliases.append(suffix.group(1).strip())
            group = next((item for item in groups
                          if any(alias and alias in item for alias in aliases)), None)
            if group is None:
                continue
            explicitly_offscreen = bool(re.search(
                r"画外|不入画|不进画|未入画|不在画内|不入镜|不在镜内|镜外", group))
            if re.search(r"看向画外|望向画外|朝画外|面向画外|视线朝画外", group):
                explicitly_offscreen = False
            partial_visible = "局部" in group and not explicitly_offscreen
            in_frame = bool(character.get("inFrame"))
            if (in_frame and explicitly_offscreen) or (not in_frame and partial_visible):
                errors.append(
                    f"阶段3 站位/分镜画内人物冲突：{shot}「{name}」overlay inFrame={in_frame}，"
                    f"分镜列“{group}”")
    return errors


def stage3(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    table = _pick(internal, ["04-*.md", "04-片段*.md", "分镜*.md"])
    shards: list[Path] = []
    if table is None:
        for sub in ("分镜编译", "分片", "04-分镜"):
            d = internal / sub
            if d.is_dir():
                shards = sorted(p for p in d.glob("*.md") if p.stat().st_size > 0)
                if shards:
                    break
    if table is None and not shards:
        errors.append("阶段3 缺少落盘物「片段规划与逐镜表」（查找模式 04-*.md 或 分镜编译/E*.md）")
        return errors, warnings
    text = table.read_text(encoding="utf-8") if table else "\n".join(p.read_text(encoding="utf-8") for p in shards)
    continuity_errors, continuity_warnings = continuity.check_project(workdir, text, "storyboard")
    errors.extend(f"阶段3 {e}" for e in continuity_errors)
    warnings.extend(f"阶段3 {w}" for w in continuity_warnings)
    table_name = table.name if table else f"分镜编译/（{len(shards)} 集）"
    exempt_items = stage_exemptions(workdir)

    # 将阶段1冻结的片段清单与阶段3实际分镜标题对账，防止只交一部分分镜却被当作整阶段完成。
    # 旧项目没有结构化 02a 时保留兼容；当前工作流项目有 02a 时，覆盖缺口是阻断项。
    plan_path = internal / "02a-结构化拍摄剧本.json"
    if plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"阶段3 片段覆盖核对无法读取 02a-结构化拍摄剧本.json：{exc}")
        else:
            planned_segments = plan.get("segments", [])
            episode_counters: dict[int, int] = {}
            expected_ids: list[str] = []
            if isinstance(planned_segments, list):
                for segment in planned_segments:
                    if not isinstance(segment, dict) or not isinstance(segment.get("episode"), int):
                        continue
                    episode = segment["episode"]
                    episode_counters[episode] = episode_counters.get(episode, 0) + 1
                    expected_ids.append(f"E{episode:02d}_SH{episode_counters[episode]:02d}")
            if not expected_ids:
                errors.append("阶段3 片段覆盖核对失败：02a-结构化拍摄剧本.json 没有可识别的 segments[].episode")
            else:
                try:
                    cross_for_coverage = _load_crosscheck()
                    actual_ids = [
                        label for label, _ in cross_for_coverage.segment_documents(text)
                        if re.fullmatch(r"E\d{2}_SH\d{2}", label)
                    ]
                except Exception as exc:  # noqa: BLE001 - 覆盖核对不能静默跳过
                    actual_ids = []
                    errors.append(f"阶段3 片段覆盖核对无法解析逐镜分段（{exc}）")
                expected_set, actual_set = set(expected_ids), set(actual_ids)
                missing_ids = [item for item in expected_ids if item not in actual_set]
                unexpected_ids = [item for item in actual_ids if item not in expected_set]
                duplicates = sorted({item for item in actual_ids if actual_ids.count(item) > 1})
                if missing_ids or unexpected_ids or duplicates:
                    details = []
                    if missing_ids:
                        details.append("缺少 " + "、".join(missing_ids))
                    if unexpected_ids:
                        details.append("计划外 " + "、".join(unexpected_ids))
                    if duplicates:
                        details.append("重复 " + "、".join(duplicates))
                    errors.append("阶段3 片段覆盖与阶段1计划不一致：" + "；".join(details))

    def _content(label: str, aliases: tuple, **kw) -> None:
        if label in exempt_items:
            warnings.append(f"阶段3「{label}」已登记阶段门豁免，按缺口放行")
            return
        _require_section(errors, text, "阶段3", aliases, **kw)

    _content("视感自查", ("视感自查", "逐镜视感", "视感统计", "视感"), min_chars=30)
    _content("上下文衔接自查", ("上下文衔接", "衔接自查", "衔接"), min_chars=40, min_rows=1,
             need_words=DIM_WORDS)
    _content("群像自检", ("群像自检", "群像自查"), min_chars=20, min_rows=1)
    _content("持物链承接", ("持物链承接", "持物链", "道具链"), min_chars=20, min_rows=1)

    # 视感自查交叉校验：声明值必须与逐镜表实算值一致，配额按实算值判定
    if "视感交叉校验" in exempt_items or "视感自查" in exempt_items:
        warnings.append("阶段3 视感交叉校验已登记阶段门豁免，按缺口放行")
    else:
        try:
            cross = _load_crosscheck()
            c_errors, c_warnings = cross.check_text(text, table_name)
        except Exception as exc:  # noqa: BLE001 - 脚本缺失不能静默放行
            errors.append(f"阶段3 视感交叉校验无法执行（{exc}）：需同目录 scripts/crosscheck_storyboard.py")
        else:
            errors.extend(f"阶段3 {e}" for e in c_errors)
            warnings.extend(f"阶段3 {w}" for w in c_warnings)
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    risk = risk_shots_from_text(text, names)
    space = internal / "04b-站位图"
    overlays = sorted(space.glob("E*_SH*_S*.json")) if space.is_dir() else []
    if exempt:
        warnings.append("站位层：已按输入单登记豁免（阶段3 不要求镜级增量）")
    else:
        if risk and not overlays:
            errors.append(f"阶段3 站位层：风险镜头 {len(risk)} 个，但 内部/04b-站位图 下没有任何镜级增量")
        for o in overlays:
            try:
                doc = json.loads(o.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{o.name} JSON 解析失败：{exc}")
                continue
            for key in ("base", "shot", "timecode", "camera", "characters"):
                if key not in doc:
                    errors.append(f"{o.name} 缺字段 {key}")
        if table is not None:
            errors.extend(_space_cast_conflicts(text, overlays))
        if (risk or overlays) and not (space / "站位继承表.md").exists():
            errors.append("阶段3 缺内部/04b-站位图/站位继承表.md（由 scripts/build_blocking_table.py 生成）")
    return errors, warnings


def stage35(workdir: Path, names: list) -> tuple[list, list]:
    """阶段 3.5 打斗路由：A/B/C 判定必须落盘。

    为什么单独设门（2026-10-23 审计）：A 级「一镜到底」会豁免镜数带与硬切计数，
    等于绕开 R8 的机检；而 04b-打斗路由判定表 此前没有任何脚本或门检查——
    一个可以合法豁免硬规的出口，没人守。
    """
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    exempt_items = stage_exemptions(workdir)
    if "打斗路由" in exempt_items or "阶段3.5" in exempt_items:
        warnings.append("阶段3.5 打斗路由已登记阶段门豁免，按缺口放行")
        return errors, warnings

    path = _pick(internal, ["04b-*打斗*.md", "04b-*路由*.md", "*打斗路由*.md"])
    source = path.name if path else ""
    if path is not None:
        text = path.read_text(encoding="utf-8")
    else:
        # 兼容：判定表内嵌在分镜文件里的写法（逐集「### 打斗路由判定」小节）
        text = ""
        for f in sorted(internal.glob("分镜编译/*.md")) + sorted(internal.glob("04-*.md")):
            body = f.read_text(encoding="utf-8")
            if "打斗路由" in body:
                text += body + "\n"
                source = source or f.name
        if not text.strip():
            errors.append("阶段3.5 缺打斗路由判定表（内部/04b-打斗路由判定表.md）："
                          "逐片段 A/B/C 判定；全剧无打斗也须写一行「全剧无打斗段，逐片段均为 C」")
            return errors, warnings
        warnings.append(f"阶段3.5 判定内嵌在「{source}」里：已按内嵌判定放行，"
                        "建议按阶段检查单单独落盘 内部/04b-打斗路由判定表.md")
    if len(text.strip()) < 40:
        errors.append(f"阶段3.5「{source}」内容过短（<40 字符），视为未判定")
        return errors, warnings

    rows = _table_rows(text)
    grades: list[str] = []
    for row in rows:
        for cell in row:
            token = cell.strip()
            if re.fullmatch(r"[ABC]", token):
                grades.append(token)
                break
            if re.match(r"^[ABC]\s*[级—\-－]", token):
                grades.append(token[0])
                break
    if not grades:
        # 内嵌散文写法：「C——纯叙述开场」「A 级：…」
        grades = re.findall(r"^\s*([ABC])\s*[级]?\s*[—\-－:：]", text, re.M)
    if not grades:
        if re.search(r"全剧\s*无打斗|均为\s*C", text):
            warnings.append("阶段3.5 全剧无打斗段，按「均为 C」声明放行")
            return errors, warnings
        errors.append(f"阶段3.5「{path.name}」未识别到 A/B/C 等级：需逐片段一行，等级单列一格")
        return errors, warnings

    if "A" in grades:
        for word, hint in (("拍点", "A 级须给拍点逐镜表"), ("一镜到底", "A 级须标明一镜到底段")):
            if word not in text:
                errors.append(f"阶段3.5 有 A 级判定但缺「{word}」：{hint}")
        if "证据" not in text and "原句" not in text:
            errors.append("阶段3.5 A 级判定缺原文证据（须引用剧本/原文原句）")
    warnings.append(f"阶段3.5 判定表含 {len(grades)} 条片段判定（A {grades.count('A')} / "
                    f"B {grades.count('B')} / C {grades.count('C')}）")
    return errors, warnings


def stage4(workdir: Path, names: list) -> tuple[list, list]:
    errors: list[str] = []
    warnings: list[str] = []
    internal = workdir / "内部"
    canonical = workdir / "精简制作包.md"
    pkgs = [canonical] if canonical.is_file() else []
    if not pkgs:
        errors.append("阶段4 找不到唯一规范交付包（精简制作包.md）")
        return errors, warnings
    continuity_errors, continuity_warnings = continuity.check_project(
        workdir, canonical.read_text(encoding="utf-8"), "prompt")
    errors.extend(f"阶段4 {e}" for e in continuity_errors)
    warnings.extend(f"阶段4 {w}" for w in continuity_warnings)
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    if exempt:
        warnings.append("站位层：已按输入单登记豁免")
    branch_rows = re.findall(
        r"^\|\s*生成轨\s*\|\s*([^|]*?)\s*\|\s*$", brief, re.M | re.I)
    if len(branch_rows) != 1 or branch_rows[0].lower() not in {"seedance25", "wan30", "h3"}:
        errors.append(
            "阶段4 无法读取唯一生成轨：输入单必须且只能登记一个有效值（seedance25、wan30 或 h3）")
        return errors, warnings
    branch = branch_rows[0].lower()
    tier_match = re.search(r"\b(tier[123]_[A-Za-z0-9_]+)\b", brief)
    h3_mode = "official" if re.search(r"h3[-_ ]?segments\s*[=:：]\s*official", brief, re.I) else "app"
    compact_validator = Path(__file__).resolve().parent / "validate_compact_package.py"
    wan_audit = Path(__file__).resolve().parent / "audit_wan30_antipatterns.py"
    for pkg in pkgs:
        command = [sys.executable, str(compact_validator), str(pkg), "--model", branch]
        if branch == "seedance25" and tier_match:
            command.extend(["--tier", tier_match.group(1)])
        if branch == "h3":
            command.extend(["--h3-segments", h3_mode])
        checked = subprocess.run(command, cwd=workdir, capture_output=True, text=True)
        if checked.returncode:
            detail = (checked.stdout + checked.stderr).strip()
            errors.append(f"{pkg.name}：登记轨 {branch} 的制作包校验失败（rc={checked.returncode}）\n{detail}")
        if branch == "wan30":
            audit_command = [sys.executable, str(wan_audit), str(pkg), "--strict"]
            dispositions = internal / "05a-Wan风险处置.json"
            if dispositions.is_file():
                audit_command.extend(["--review-record", str(dispositions)])
            audited = subprocess.run(
                audit_command,
                cwd=workdir, capture_output=True, text=True)
            if audited.returncode:
                detail = (audited.stdout + audited.stderr).strip()
                errors.append(f"{pkg.name}：Wan3.0反例专项审计失败（rc={audited.returncode}）\n{detail}")
    if exempt:
        return errors, warnings
    space = internal / "04b-站位图"
    overlays = list(space.glob("E*_SH*_S*.json")) if space.is_dir() else []
    for pkg in pkgs:
        text = pkg.read_text(encoding="utf-8")
        risk = risk_shots_from_text(text, names)
        if risk and not overlays:
            errors.append(
                f"{pkg.name}：命中风险闸门（{len(risk)} 个多人同框镜头）但站位层为空"
                f"（内部/04b-站位图 {'不存在' if not space.is_dir() else '无镜级增量'}）")
    return errors, warnings


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser(description="阶段出口门：检查各阶段的落盘物是否齐备")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("--stage", choices=["2", "3", "3.5", "4", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    workdir = args.workdir
    if not workdir.is_dir():
        print(f"作品目录不存在：{workdir}", file=sys.stderr)
        return 2
    names = char_names(workdir)
    stages = ["2", "3", "3.5", "4"] if args.stage == "all" else [args.stage]
    all_errors: list[str] = []
    all_warnings: list[str] = []
    stage_results: dict[str, dict] = {}
    for st in stages:
        fn = {"2": stage2, "3": stage3, "3.5": stage35, "4": stage4}[st]
        errs, warns = fn(workdir, names)
        if st == "2":
            review_errors: list[str] = []
            workflow_manifest.check_review_stage1(workdir / "内部", True, review_errors, [])
            errs.extend(review_errors)
        elif st == "4":
            review_errors = []
            workflow_manifest.check_review_stage4(
                workdir / "内部", workdir / "精简制作包.md", True, review_errors, [])
            errs.extend(review_errors)
            ledger_file = workdir / "内部" / ledger.LEDGER_NAME
            if not ledger_file.is_file():
                errs.append("阶段4 缺少批次台账；全覆盖评审后须登记各提示词批次通过状态")
            else:
                try:
                    ledger_data = ledger.load_ledger(workdir)
                    ledger_errors, _ = ledger.diagnose(workdir, ledger_data)
                    errs.extend(f"阶段4 批次台账：{item}" for item in ledger_errors)
                    prompt_batches = [entry for entry in ledger_data.get("batches", [])
                                      if str(entry.get("stage")) == "4"]
                    if not prompt_batches:
                        errs.append("阶段4 批次台账中没有提示词批次记录")
                    for entry in prompt_batches:
                        if entry.get("state") != "通过":
                            errs.append(f"阶段4 提示词批次 {entry.get('batch_id', '?')} 尚未通过全覆盖评审")
                        if entry.get("gate_errors") != 0:
                            errs.append(f"阶段4 提示词批次 {entry.get('batch_id', '?')} 缺少有效的 0 错误本地门结果")
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    errs.append(f"阶段4 批次台账不可读取：{exc}")
        stage_results[st] = {"errors": errs, "warnings": warns}
        for e in errs:
            all_errors.append(f"[阶段{st}] {e}")
        for w in warns:
            all_warnings.append(f"[阶段{st}] {w}")
    receipt_path = workdir / "内部" / "阶段门记录.json"
    if receipt_path.parent.is_dir():
        try:
            receipts = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else {
                "schema": "stage-gate-receipts/1", "stages": {}}
            receipts.setdefault("stages", {})
        except (json.JSONDecodeError, OSError):
            receipts = {"schema": "stage-gate-receipts/1", "stages": {}}
        for st, outcome in stage_results.items():
            if st not in {"2", "3", "3.5"}:
                continue
            receipts["stages"][st] = {
                "status": "通过" if not outcome["errors"] else "失败",
                "errors": len(outcome["errors"]),
                "warnings": len(outcome["warnings"]),
                "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "inputs": wc.stage_gate_inputs(workdir, st),
                "error_details": outcome["errors"],
            }
        receipts["schema"] = "stage-gate-receipts/1"
        receipt_path.write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"ok": not all_errors, "stage": args.stage, "errors": all_errors,
              "warnings": all_warnings,
              "receipt": str(receipt_path) if receipt_path.is_file() else None}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        for w in all_warnings:
            print(f"  提醒：{w}")
        for e in all_errors:
            print(f"  错误：{e}")
        print(f"\n阶段出口门：{'通过' if not all_errors else '失败'}（{len(all_errors)} 错误 / {len(all_warnings)} 提醒）")
        if receipt_path.is_file():
            print(f"阶段门版本收据：{receipt_path}")
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
