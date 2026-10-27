#!/usr/bin/env python3
"""派单卡生成器：从输入单与 policy.json 机械构造阶段 3/4 的执行员交接包。

为什么有这个脚本（2026-10-25 流程优化）
--------------------------------------------------------------------------
交接包模板（R17）要求总控「从输入单逐字抄录生成轨、字符档、校验命令」。抄写环节
出过真实事故（2026-10-22 座次表写反）：总控臆断或抄错一个参数，执行员只信派单，
错误会一路带进成片。本脚本把「抄写」变成「构造」：

  · 生成轨、字符预算、硬切带、校验命令全部从输入单 + policy.json 读取；
  · 生成轨缺失/无效/重复时**失败关闭**（R37），不静默回退默认轨；
  · 上游产物缺失或为空时报错（PROC-05：下游不得在上游落盘物缺失时开工）；
  · 每个上游文件附 SHA-256（批次版本锁，评审记录必须引用同一哈希）；
  · 卡内附规范快照（policy 版本与哈希）与「规则应用清单」，执行员阶段报告
    必须逐条回答规则落在哪里——验证「用没用」，不验证「读没读」。

总控仍负责两件脚本替代不了的事：【依据原句】逐字引用正文出处；边界片段的
语义裁决。其余字段一律以本脚本输出为准，总控手工改动数值视为违规派单。

用法：
    python3 build_handoff.py <作品目录> --stage 4 --batch "E03-SH01~SH04"
    python3 build_handoff.py <作品目录> --stage 3 --batch "E02-SH02~SH06" --out <路径.md>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import workflow_common as wc  # noqa: E402  口径唯一实现（改造六）


def _sha256(path: Path) -> str:
    return wc.sha256_file(path)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _pick(internal: Path, patterns: list) -> Path | None:
    for pat in patterns:
        hits = sorted(internal.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None


def _stage4_space_files(internal: Path, segment_ids: list[str]) -> list[tuple[str, Path]]:
    """Return only the frozen scene base and shot overlays used by this prompt batch.

    Numeric blocking stays internal, but prompt authors need the matching contracts
    to compile positions and eyelines faithfully. Never expose the whole 04b folder.
    """
    space_dir = internal / "04b-站位图"
    if not space_dir.is_dir():
        return []
    rows: list[tuple[str, Path]] = []
    seen_bases: set[str] = set()
    for segment_id in segment_ids:
        prefix = wc.normalize_seg_id(segment_id).replace("-", "_") + "_S"
        overlays = sorted(path for path in space_dir.glob(f"{prefix}*.json") if path.is_file())
        for overlay in overlays:
            try:
                data = json.loads(overlay.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"阶段4站位增量不可读取：{overlay.name}: {exc}") from exc
            base_name = data.get("base")
            if not isinstance(base_name, str) or not base_name.strip():
                raise ValueError(f"阶段4站位增量缺少 base 字段：{overlay.name}")
            base_path = space_dir / f"{base_name}.json"
            if not base_path.is_file():
                raise ValueError(f"阶段4站位增量引用的场景基底不存在：{overlay.name} → {base_path.name}")
            if base_name not in seen_bases:
                rows.append((f"站位场景基底 {base_name}", base_path))
                seen_bases.add(base_name)
            rows.append((f"镜级站位增量 {data.get('shot', overlay.stem)}", overlay))
    return rows


def _fail(messages: list) -> int:
    for m in messages:
        print(f"错误：{m}", file=sys.stderr)
    print("派单卡未生成（失败关闭；先回补上游再派单，禁止手工填卡绕过）", file=sys.stderr)
    return 1


def _review_sections_pass(text: str, labels: tuple[str, ...]) -> list[str]:
    """阶段 1 三个交接点必须各自有明确的通过结论。"""
    errors = []
    for label in labels:
        section = wc.markdown_section(text, label)
        verdict = re.search(r"^\s*(?:[-*]\s*)?结论\s*[：:]\s*([^\n。；;，,]+)", section or "", re.M)
        if not verdict or verdict.group(1).strip() != "通过":
            errors.append(f"01c 缺少「{label}」交接点评审的明确通过结论")
    if not re.search(r"未关闭阻断/重要缺陷\s*[：:]\s*0\b", text):
        errors.append("01c 缺少「未关闭阻断/重要缺陷：0」放行行")
    if not re.search(r"(评稿人|评审人|子任务|模型)", text):
        errors.append("01c 未标明独立评审人")
    return errors


def _single_review_pass(path: Path, label: str) -> list[str]:
    if not path.is_file():
        return [f"缺少独立评审记录：{path}"]
    text = path.read_text(encoding="utf-8")
    if not re.search(r"(?:总体)?结论\s*[：:]\s*通过(?:\s*[，,。；;]|$)", text, re.M):
        return [f"{label}评审没有明确的通过结论：{path.name}"]
    if not re.search(r"未关闭阻断/重要缺陷\s*[：:]\s*0\b", text):
        return [f"{label}评审缺少「未关闭阻断/重要缺陷：0」放行行：{path.name}"]
    if not re.search(r"(评稿人|评审人|子任务|模型)", text):
        return [f"{label}评审未标明独立评审人：{path.name}"]
    return []


def _gate_receipt_errors(workdir: Path, required: list[str]) -> list[str]:
    path = workdir / "内部" / "阶段门记录.json"
    if not path.is_file():
        return ["缺少阶段门记录；请按顺序运行阶段 2、3、3.5 出口门后再派单"]
    try:
        receipts = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"阶段门记录不可读取：{exc}"]
    if receipts.get("schema") != "stage-gate-receipts/1":
        return ["阶段门记录版本不匹配；重跑阶段出口门生成当前记录"]
    errors = []
    for stage in required:
        record = (receipts.get("stages") or {}).get(stage)
        if not record or record.get("status") != "通过" or record.get("errors") != 0:
            errors.append(f"阶段 {stage} 缺少有效的 0 错误出口门记录")
            continue
        if record.get("inputs") != wc.stage_gate_inputs(workdir, stage):
            errors.append(f"阶段 {stage} 出口门后的输入版本已变化；重跑该阶段门，不重做未变内容评审")
    return errors


def check_stage_unlock(workdir: Path, stage: str) -> list[str]:
    """真正拦截阶段 3/4 派单；阶段门收据与独立评审都须仍对应当前版本。"""
    internal = workdir / "内部"
    errors: list[str] = []
    stage1_review = internal / "01c-剧情评审.md"
    if not stage1_review.is_file():
        errors.append("阶段 1 缺少内部/01c-剧情评审.md")
    else:
        errors.extend(_review_sections_pass(
            stage1_review.read_text(encoding="utf-8"), ("事件/分集", "逐集剧本", "片段规划")))

    stage2_review = _pick(internal, ["03b-资产评审.md", "03b-*评审*.md"])
    if stage2_review is None:
        errors.append("阶段 2 缺少独立资产评审记录（内部/03b-资产评审.md）")
    else:
        errors.extend(_single_review_pass(stage2_review, "阶段 2 资产"))

    required_gates = ["2"] if stage == "3" else ["2", "3", "3.5"]
    errors.extend(_gate_receipt_errors(workdir, required_gates))

    if stage == "4":
        ledger_path = internal / "批次台账.json"
        if not ledger_path.is_file():
            errors.append("阶段 3 缺批次台账；先同步所有分镜批次并完成独立复核")
        else:
            try:
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                ledger = {"batches": []}
                errors.append(f"阶段 3 批次台账不可读取：{exc}")
            stage3 = [entry for entry in ledger.get("batches", [])
                      if str(entry.get("stage")) == "3"]
            if not stage3:
                errors.append("阶段 3 批次台账中没有分镜批次记录")
            else:
                sys.path.insert(0, str(SCRIPTS))
                import batch_ledger as bl  # noqa: E402
                ledger_errors, _ = bl.diagnose(workdir, ledger)
                errors.extend(f"分镜批次台账：{item}" for item in ledger_errors)
                for entry in stage3:
                    bid = entry.get("batch_id", "?")
                    if entry.get("state") != "通过":
                        errors.append(f"分镜批次 {bid} 尚未通过独立复核")
                    if entry.get("gate_errors") != 0:
                        errors.append(f"分镜批次 {bid} 缺少有效的 0 错误批次门结果")
                    review_rel = entry.get("review")
                    review_path = workdir / review_rel if review_rel else None
                    if not review_path or not review_path.is_file():
                        errors.append(f"分镜批次 {bid} 缺独立评审文件")
                        continue
                    review_text = review_path.read_text(encoding="utf-8")
                    if not re.search(r"分镜批次复核结论\s*[：:]\s*通过", review_text):
                        errors.append(f"分镜批次 {bid} 评审缺「分镜批次复核结论：通过」")
                    if not re.search(r"打斗路由复核结论\s*[：:]\s*通过", review_text):
                        errors.append(f"分镜批次 {bid} 评审缺「打斗路由复核结论：通过」")
                    if not re.search(r"未关闭阻断/重要缺陷\s*[：:]\s*0\b", review_text):
                        errors.append(f"分镜批次 {bid} 评审缺「未关闭阻断/重要缺陷：0」")
    return errors


def load_track(brief_text: str) -> str:
    """读输入单的唯一生成轨；缺失/无效/重复一律抛错（R37 失败关闭）。

    接受 `| 生成轨 | wan30 |`、`生成模型轨`、存量项目的 `| 生成模型 | Wan3.0（--model wan30 轨）|`
    等写法，归一化后返回。实现在 workflow_common，此处只做异常转译。
    """
    return wc.read_track(brief_text)


def load_char_budget(policy: dict, brief_text: str, track: str) -> dict:
    """字符与硬切口径只从登记轨的 profile 读取（R37：禁止跨轨回退）。"""
    return wc.char_budget(policy, brief_text, track)


UPSTREAM = {
    "3": [
        ("阶段1 冻结分段计划", ["02a-结构化拍摄剧本.json"], True),
        ("本集剧本", ["02-逐集拍摄剧本.md", "01-*.md"], True),
        ("资产与空间设计", ["03-资产与空间设计.md", "03-*.md", "02-资产*.md"], True),
        ("项目输入单", ["00-*输入单*.md", "00-*.md"], True),
    ],
    "4": [
        ("片段规划与逐镜表（冻结版）", ["04-片段规划与逐镜表.md", "04-*.md"], True),
        ("衔接事实（阶段3冻结）", ["04c-衔接事实.json"], True),
        ("阶段1冻结片段边界与对白/动作容量", ["04a-片段边界.json"], True),
        ("资产与空间设计（母版冻结）", ["03-资产与空间设计.md", "03-*.md", "02-资产*.md"], True),
        ("固定资产图片提示词（阶段2锁定母版）", ["03a-固定资产图片提示词.md"], True),
        ("项目输入单", ["00-*输入单*.md", "00-*.md"], True),
        ("打斗路由判定表", ["04b-打斗路由判定表.md", "04b-*路由*.md"], True),
    ],
}

MUST_READ = {
    "3": [
        "references/story-evaluation.md",
        "references/content-expression.md",
        "../../../补充资源/小墨个人分镜SKILL6.3（豪华升级版）.md",
        "../zhifeiji-workflow-router/references/workflows.md#w14",
        "references/micro-expression-layer.md",
        "references/fight-router.md",
    ],
    "4": [
        "references/prompt-layering.md",
        "references/prompt-review.md",
        "references/content-expression.md",
        "references/voice-and-dubbing.md",
        "references/compact-import.md",
        "references/micro-expression-layer.md",
        "../../../23 真人感微表情AI视频Skill/人物微表情表演skill.zip#micro-expression-video-generator/references/muscle-dispatch-library.md",
        "../../../23 真人感微表情AI视频Skill/人物微表情表演skill.zip#micro-expression-video-generator/references/tempo-density-guide.md",
        "../../../23 真人感微表情AI视频Skill/人物微表情表演skill.zip#micro-expression-video-generator/references/video-prompt-guardrails.md",
    ],
}

TRACK_MUST_READ = {
    "4": {
        "seedance25": ["../../../18 ZHIFEIJI-2.5分镜提示词SKILL/Seedance2.5_通用提示词生成适配器_v1.0.md"],
        "wan30": ["references/wan30-prompt-spec.md", "references/wan30-adapter-v1.0.md"],
        "h3": ["../minimax-h3-adapter/SKILL.md", "../minimax-h3-adapter/references/asset-reference.md",
               "../../../25 minimax H3官方skill/skills/h3-prompt-writing/references/base-en.txt",
               "../../../25 minimax H3官方skill/skills/h3-prompt-writing/references/ref-en.txt"],
    },
}

RULES = {
    "3": ["R5 上下文衔接", "R12 多智能体隔离", "R17 交接包白名单", "R27 视感自查表（crosscheck_storyboard）",
          "R28 打斗路由判定表", "R36 分镜完整覆盖阶段1计划", "R38 剧情保留与敏感内容表达"],
    "4": {
        "seedance25": ["R1 四段结构", "R2 自然语言镜头行", "R3 声音来源标签", "R4 声线锁定", "R8 时长/切数/字符档", "R10 包内零编号", "R31 分层与去重"],
        "wan30": ["R1 四段结构", "R2 自然语言（Wan 按 R20 镜头前置）", "R3 声音来源标签", "R4 声线锁定", "R8 Wan 字符口径", "R20 镜头前置",
                  "R21b 包内零编号", "R22 Wan 反例硬规则", "R23 人物分身预防", "R31 分层与去重", "R32 参考图预算", "R33 锚词全包同源",
                  "R34 服装锚三项", "R35 文字物理规避"],
        "h3": ["R25 H3 官方字段结构", "R4 声线锚点写进说话人描述", "R31 分层与去重"],
    },
}


def parse_batch_ids(batch: str) -> list:
    """解析批次范围：支持 "E03-SH01~SH04" 区间与逗号列表。"""
    return wc.parse_batch_ids(batch)


def resolve_batch(batch: str, table_text: str | None) -> list:
    ids = parse_batch_ids(batch)
    if table_text is None:
        return ids
    found = set(wc.segment_ids(table_text))
    missing = [i for i in ids
               if wc.normalize_seg_id(i) not in found
               and not any(wc.normalize_seg_id(i) in f or f in wc.normalize_seg_id(i) for f in found)]
    if missing:
        raise ValueError(f"批次片段在冻结逐镜表中找不到：{'、'.join(missing)}"
                         "（先确认阶段 3 已落盘并冻结该片段，再派阶段 4 单）")
    return ids


def build_card(workdir: Path, stage: str, batch: str) -> str:
    internal = workdir / "内部"
    if not internal.is_dir():
        raise ValueError(f"{internal} 不存在（先完成阶段 0 落盘）")
    policy = json.loads((SKILL / "policy.json").read_text(encoding="utf-8"))
    brief_path = _pick(internal, ["00-*输入单*.md", "00-*.md"])
    if brief_path is None:
        raise ValueError("缺内部/00-项目输入单.md（阶段 0 未落盘，不能派单）")
    brief_text = brief_path.read_text(encoding="utf-8")
    track = load_track(brief_text)
    budget = load_char_budget(policy, brief_text, track)

    upstream_rows, upstream_texts = [], {}
    for label, patterns, required in UPSTREAM[stage]:
        path = _pick(internal, patterns)
        if path is None:
            if required:
                raise ValueError(f"缺上游落盘物「{label}」（查找模式 {' / '.join(patterns)}）——"
                                 "PROC-05：上游缺失时下游不得开工")
            upstream_rows.append(f"- {label}：未落盘（可选，命中打斗段时必须补齐后再派单）")
            continue
        upstream_rows.append(f"- {label}：{path}（SHA-256 {_sha256(path)[:16]}…）")
        upstream_texts[label] = path.read_text(encoding="utf-8")

    check_table = upstream_texts.get("片段规划与逐镜表（冻结版）") if stage == "4" else None
    ids = resolve_batch(batch, check_table)
    stage4_space_files = _stage4_space_files(internal, ids) if stage == "4" else []
    batch_band = wc.recommended_batch_size(policy, track)

    stage4_unlock = ""
    if stage == "4":
        stage4_unlock = ("【放行前提】阶段 1 剧情评审、阶段 2 资产评审与出口门、阶段 3 分镜出口门、阶段 3.5 打斗路由出口门均通过；"
                         "阶段 0–3.5 的必需产物和评审记录齐全、上游版本哈希冻结。"
                         "（政策 stage4_unlock；总控派单前核对执行账与门记录，本卡不代为声明）\n")

    must_read = list(MUST_READ[stage]) + TRACK_MUST_READ.get(stage, {}).get(track, [])
    rules = RULES[stage] if stage == "3" else RULES[stage][track]
    if stage == "4":
        rules = rules + ["R38 剧情保留与敏感内容表达"]
    snapshot = (f"policy v{policy.get('policy_version', '?')}（policy.json SHA-256 {_sha256(SKILL / 'policy.json')[:16]}…）")

    lines = [
        f"【阶段】{stage} " + ("片段与分镜" if stage == "3" else "最终提示词") + f"（本批：{batch}）",
        f"【批次与版本锁】批次 ID：S{stage}-{wc.batch_id(batch, brief_path)}；"
        f"片段清单：{'、'.join(ids)}",
        f"【批次负载】本批 {len(ids)} 段；{track} 建议每批 {batch_band[0]}–{batch_band[1]} 段。"
        "此范围只用于安排执行员负载，用户指定的片段边界与范围优先",
    ]
    lines += upstream_rows
    if stage == "4" and stage4_space_files:
        lines.append("【本批镜级站位合同】仅读取以下匹配的冻结场景基底与镜级增量，不扫描04b全目录；正文将坐标转成自然语言，不输出数值坐标。")
        for label, path in stage4_space_files:
            lines.append(f"- {label}：{path}（SHA-256 {_sha256(path)[:16]}…）")
    lines += [
        f"【规范快照】{snapshot}；派单卡由 build_handoff.py 生成，数值改动须先改输入单/policy 并重新生成",
        stage4_unlock.rstrip(),
        f"【唯一生成轨】{track}（从输入单逐字读取）；只用该轨适配器、格式和校验器；"
        + ("Wan/H3 禁止传 --tier" if track != "seedance25" else f"--tier {budget['tier']}"),
        f"【字符口径】{budget['chars']}",
        f"【硬切带】{budget['hard_cuts']}",
        "【必读（白名单）】",
    ]
    for reference in must_read:
        path, marker, anchor = reference.partition("#")
        resolved = (SKILL / path).resolve()
        if not resolved.is_file():
            raise ValueError(f"派单必读文件不存在：{resolved}")
        lines.append(f"- {resolved}" + (f"#{anchor}" if marker else ""))
    lines += [
        "【上游输入】上方所列上游产物为唯一输入事实；发现上游矛盾时挂起回报总控，不自行修正",
        "【产出】内部/派单/" + ("{批次名}_分镜.md 与专属 overlay" if stage == "3" else "{批次名}_提示词草稿.md（隔离草稿，不并发写最终包）"),
        "【依据原句】本派单里每个事实约束的正文出处（逐字原句＋集/片段/镜头）；给不出原句的约束不得下派",
    ]
    if stage == "3":
        lines.append(f"【批次本地校验】python3 {SCRIPTS / 'crosscheck_storyboard.py'} <本批分镜稿>"
                     + (f" --tier {budget['tier']}" if track == "seedance25" else ""))
        lines.append(f"【风险镜站位校验】命中站位闸门时运行 python3 {SCRIPTS / 'validate_space_blocking.py'} <本批站位目录>")
        lines.append(f"【闸口】① 硬切口径：{budget['hard_cuts']}；时间轴连续并按登记轨粒度 ② 上下镜与跨片段衔接闭合 "
                     "③ 台词逐字且时间容纳自然语速 ④ 视感统计与逐镜表一致（crosscheck_storyboard.py） "
                     "⑤ 打斗 A/B/C 逐片段落盘 ⑥ 独立评审记录引用本批哈希")
    else:
        command = f"python3 {SCRIPTS / 'validate_compact_package.py'} <本批临时包> --model {track}"
        if track == "seedance25":
            command += f" --tier {budget['tier']}"
        elif track == "h3" and "--h3-segments official" in budget['validator']:
            command += " --h3-segments official"
        lines.append(f"【批次本地校验】{command}")
        if track == "wan30":
            lines.append(f"【Wan本地风险扫描】python3 {SCRIPTS / 'audit_wan30_antipatterns.py'} <本批临时包>"
                         "（硬错阻断，warning登记待独立评审，不以本地扫描代替风险验收）")
            lines.append(f"【Wan全集放行】python3 {SCRIPTS / 'audit_wan30_antipatterns.py'} <最终包> --strict"
                         " --review-record 内部/05a-Wan风险处置.json（有风险时由独立评审逐项留证；无风险无需记录文件）")
        lines.append("【闸口】① 模板按轨（Seedance/Wan 四段，H3 官方字段），无【参数】 ② 时间轴按本轨粒度连续覆盖 "
                     "③ 七类声音标签＋「口型」；声线锁定行逐字取母版 ④ 表演线索每镜≤2、片段≤4 ⑤ 字符口径按轨 "
                     "⑥ 分层与去重：三锚/场景机位/道具状态，不重写资产已锁事实 ⑦ 本批机械硬错清零，风险保留待全集独立评审处置")
    lines.append("【规则应用清单】本批阶段报告必须逐条回答以下规则落在哪些行（给位置与证据；未用到的写「本批不适用＋原因」）：")
    lines += [f"- {r}" for r in rules]
    lines += [
        "【禁止】不读后续阶段规范；不写最终包；" + ("不预写 @Image/《Picture》编号" if stage == "4" else "不为凑切镜加无信息镜头")
        + "；不改台词；不临场改音色",
        "【返回】结论(通过/挂起/失败)／证据路径／产出文件 SHA-256／每条字符数（阶段4）／规则应用清单／未决问题",
    ]
    return "\n".join(lines) + "\n"


def build_manifest(workdir: Path, stage: str, batch: str, card_text: str) -> dict:
    """批次清单：把派单卡里的口径落成机器可读的一份，供台账与事后审计核对。

    改造一的后半段。派单卡给人看，manifest 给脚本看——两者由同一次 gather 生成，
    出现分歧就说明有人手改了卡（违规派单），台账 status 会直接报出来。
    """
    internal = workdir / "内部"
    if not internal.is_dir():
        raise ValueError(f"{internal} 不存在（先完成阶段 0 落盘）")
    policy = json.loads((SKILL / "policy.json").read_text(encoding="utf-8"))
    brief_path = _pick(internal, ["00-*输入单*.md", "00-*.md"])
    if brief_path is None:
        raise ValueError("缺内部/00-项目输入单.md（阶段 0 未落盘，不能派单）")
    brief_text = brief_path.read_text(encoding="utf-8")
    track = load_track(brief_text)
    budget = load_char_budget(policy, brief_text, track)

    upstream, table_text = [], None
    for label, patterns, required in UPSTREAM[stage]:
        path = _pick(internal, patterns)
        if path is None:
            if required:
                raise ValueError(f"缺上游落盘物「{label}」（查找模式 {' / '.join(patterns)}）——"
                                 "PROC-05：上游缺失时下游不得开工")
            upstream.append({"label": label, "path": None, "sha256": None, "present": False})
            continue
        try:
            rel = str(path.relative_to(workdir))
        except ValueError:
            rel = str(path)
        upstream.append({"label": label, "path": rel, "sha256": _sha256(path), "present": True})
        if label.startswith("片段规划与逐镜表"):
            table_text = path.read_text(encoding="utf-8")

    ids = resolve_batch(batch, table_text if stage == "4" else None)
    if stage == "4":
        for label, path in _stage4_space_files(internal, ids):
            try:
                rel = str(path.relative_to(workdir))
            except ValueError:
                rel = str(path)
            upstream.append({"label": label, "path": rel, "sha256": _sha256(path), "present": True})
    snapshot = wc.policy_snapshot(policy)
    return {
        "schema": "handoff-manifest/1",
        "generated_by": "build_handoff.py",
        "stage": stage,
        "batch": batch,
        # Same segment range is commonly dispatched once for storyboard and again for
        # prompt compilation. Keep the phase in the key so ledger sync cannot merge them.
        "batch_id": f"S{stage}-{wc.batch_id(batch, brief_path)}",
        "segments": ids,
        "recommended_batch_segments": wc.recommended_batch_size(policy, track),
        "segment_upstream": {
            seg_id: wc.sha256_text(block.strip())
            for seg_id, block in wc.split_segments(table_text or "")
            if wc.normalize_seg_id(seg_id) in {wc.normalize_seg_id(i) for i in ids}
        } if stage == "4" else {},
        "continuity_upstream": wc.continuity_scope_snapshot(
            internal / "04c-衔接事实.json", ids) if stage == "4" else {},
        "track": track,
        "tier": budget["tier"],
        "char_budget": budget,
        "policy": snapshot,
        "upstream": upstream,
        "card_sha256": wc.sha256_text(card_text),
        "state": "待写",
        "review_sha256": None,
        "gate": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="阶段 3/4 派单卡生成器（参数由输入单与 policy 构造，失败关闭）")
    ap.add_argument("workdir", type=Path, help="作品目录（含 内部/）")
    ap.add_argument("--stage", choices=["3", "4"], required=True)
    ap.add_argument("--batch", required=True, help='批次范围，如 "E03-SH01~SH04" 或逗号列表')
    ap.add_argument("--out", type=Path, help="写入文件（缺省打印到 stdout）")
    ap.add_argument("--manifest-out", type=Path,
                    help="批次清单 JSON 写入路径（改造一：与派单卡同源生成，供台账核对）")
    args = ap.parse_args()
    if not args.workdir.is_dir():
        print(f"作品目录不存在：{args.workdir}", file=sys.stderr)
        return 2
    try:
        if args.stage in {"3", "4"}:
            unlock_errors = check_stage_unlock(args.workdir, args.stage)
            if unlock_errors:
                return _fail(unlock_errors)
        card = build_card(args.workdir, args.stage, args.batch)
        manifest = build_manifest(args.workdir, args.stage, args.batch, card)
    except ValueError as exc:
        return _fail([str(exc)])
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(card, encoding="utf-8")
        print(f"派单卡 → {args.out}")
    else:
        print(card, end="")
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"批次清单 → {args.manifest_out}（批次 ID {manifest['batch_id']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
