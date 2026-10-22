#!/usr/bin/env python3
"""阶段出口门：每个阶段的落盘物必须齐备且自洽，缺一项即判错。

用法：
    python3 validate_stage_artifacts.py <作品目录> --stage 2
    python3 validate_stage_artifacts.py <作品目录> --stage 3
    python3 validate_stage_artifacts.py <作品目录> --stage all

为什么有这道门（2026-10-22 事故复盘）
--------------------------------------------------------------------------
上一轮《三千国道》重制时，阶段 2/3 的站位层被整段跳过，而**流水线里没有任何一道
门会因为它缺席而失败**：

  · 阶段 2/3 的落盘清单（站位基底／镜级增量／继承表）没有任何校验器检查；
  · `validate_compact_package --space-dir` 是**可选参数**，目录找不到就"跳过"；
  · 所有机检都只跑在最终交付包上，看不见上游阶段。

结果是 4 轮返工（约 50 路 agent），其中 3 轮返工的根因都是"阶段 2/3 该固化的东西
被推到了交付后"。本脚本把这些上游落盘物变成**带门的硬约束**。

判定口径
--------------------------------------------------------------------------
风险闸门（W18）：多人同框 ≥2 人／固定座位或排位／有前后排／狭小室内／
有操作位或设备承托／有人走位或离席。命中即必须建站位层。

站位层豁免：项目的 `内部/00-项目输入单.md` 写 `站位层：豁免（理由：…）` 才可跳过；
**默认必须建**。这是刻意设计成"默认要建、豁免要留痕"——反过来就等于默认可以不做。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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


# 阶段2 必有的落盘物：语义名 → 可接受的命名模式（覆盖 0X- 两套模板命名）
STAGE2_ARTIFACTS = {
    "项目输入单": ["00-*输入单*.md", "00-*.md"],
    "故事/分集规划": ["01-*分集*.md", "01-*故事*.md", "01-*.md"],
    "剧本": ["02-*剧本*.md", "01-*剧本*.md", "02-逐集拍摄剧本.md"],
    "资产与空间设计": ["03-*资产*.md", "02-*资产*.md"],
}


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

    _character_field_warnings(asset_text, _policy(), warnings)
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
    table_name = table.name if table else f"分镜编译/（{len(shards)} 集）"
    exempt_items = stage_exemptions(workdir)

    def _content(label: str, aliases: tuple, **kw) -> None:
        if label in exempt_items:
            warnings.append(f"阶段3「{label}」已登记阶段门豁免，按缺口放行")
            return
        _require_section(errors, text, "阶段3", aliases, **kw)

    _content("视感自查", ("视感自查", "逐镜视感", "视感统计"), min_chars=30)
    _content("上下文衔接自查", ("上下文衔接",), min_chars=40, min_rows=1,
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
    if path is None:
        errors.append("阶段3.5 缺打斗路由判定表（内部/04b-打斗路由判定表.md）："
                      "逐片段 A/B/C 判定；全剧无打斗也须写一行「全剧无打斗段，逐片段均为 C」")
        return errors, warnings
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < 40:
        errors.append(f"阶段3.5「{path.name}」内容过短（<40 字符），视为未判定")
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
    pkgs = sorted(workdir.glob("精简制作包*.md"))
    if not pkgs:
        errors.append("阶段4 找不到交付包（精简制作包*.md）")
        return errors, warnings
    brief = _read(_pick(internal, STAGE2_ARTIFACTS["项目输入单"]) or internal / "00-项目输入单.md")
    exempt = bool(EXEMPT_RE.search(brief))
    if exempt:
        warnings.append("站位层：已按输入单登记豁免")
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
    for st in stages:
        fn = {"2": stage2, "3": stage3, "3.5": stage35, "4": stage4}[st]
        errs, warns = fn(workdir, names)
        for e in errs:
            all_errors.append(f"[阶段{st}] {e}")
        for w in warns:
            all_warnings.append(f"[阶段{st}] {w}")
    result = {"ok": not all_errors, "stage": args.stage, "errors": all_errors, "warnings": all_warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        for w in all_warnings:
            print(f"  提醒：{w}")
        for e in all_errors:
            print(f"  错误：{e}")
        print(f"\n阶段出口门：{'通过' if not all_errors else '失败'}（{len(all_errors)} 错误 / {len(all_warnings)} 提醒）")
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
