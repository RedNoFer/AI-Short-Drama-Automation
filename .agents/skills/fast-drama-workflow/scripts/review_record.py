"""Check review coverage and versions, never infer semantic or media quality."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

QUALITY_FIELDS = ("purpose", "action_state", "visibility", "capacity", "continuity", "expression")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_review(package: Path, scripts_dir: Path) -> list[str]:
    record = package.parent / "内部" / "验收记录.json"
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"无法读取轻量验收记录：{exc}"]
    if not isinstance(data, dict):
        return ["验收记录必须为 JSON 对象"]
    errors = []
    if data.get("package_sha256") != digest(package):
        errors.append("验收记录的制作包 SHA-256 已过期，须实际复核后更新")
    mode = data.get("review_mode")
    if mode not in ("author_self_check", "independent_review") or not isinstance(data.get("reviewer"), str) or not data["reviewer"].strip():
        errors.append("须如实登记评审方式与执行者；作者自查不得冒称独立评审")
    if mode == "independent_review" and (not isinstance(data.get("author"), str) or not data["author"].strip() or data["author"] == data.get("reviewer")):
        errors.append("独立评审须登记不同的作者与评审执行者；机器不证明身份真实独立")
    media = data.get("media_status")
    if not isinstance(media, dict) or any(media.get(f) not in ("pending", "checked", "failed") for f in ("references", "submission", "video")):
        errors.append("须分别登记参考图、实际提交和成片状态，未核验填 pending")
    inputs = data.get("inputs")
    source_texts = {}
    if not isinstance(inputs, list) or not inputs:
        errors.append("缺少源文／剧本、节拍、资产等本次依据的 inputs 版本清单")
        inputs = []
    for item in inputs:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            errors.append("inputs 条目须含 file 与 sha256")
            continue
        path = package.parent / item["file"]
        try:
            if item.get("sha256") != digest(path):
                errors.append(f"依据文件已变更：{item['file']}")
            source_texts[item["file"]] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"依据文件不可读：{item['file']}")
    sys.path.insert(0, str(scripts_dir))
    from validate_compact_package import parse_structure
    parsed = parse_structure(package.read_text(encoding="utf-8"))
    expected = {(ep["code"], sh["code"]): sh["prompts"].get("视频提示词", "")
                for ep in parsed["episodes"] for sh in ep["shots"]}
    segments = data.get("segments")
    if not isinstance(segments, list):
        return errors + ["segments 必须逐段列出验收依据"]
    seen = set()
    for item in segments:
        if not isinstance(item, dict):
            errors.append("segments 条目须为对象")
            continue
        key = (item.get("episode"), item.get("shot"))
        if not all(isinstance(value, str) for value in key):
            errors.append("验收项缺少有效 episode／shot")
            continue
        label = "/".join(key)
        if key not in expected or key in seen:
            errors.append(f"验收范围多余或重复：{label}")
        seen.add(key)
        quality = item.get("quality", {})
        if not isinstance(quality, dict) or any(not isinstance(quality.get(f), str) or not quality[f].strip() for f in QUALITY_FIELDS):
            errors.append(f"{label} 缺少六项具体质量判断")
        quote = item.get("prompt_quote")
        if not isinstance(quote, str) or not quote.strip() or quote not in expected.get(key, ""):
            errors.append(f"{label} 提示词引文不存在")
        source_file = item.get("source_file")
        source = source_texts.get(source_file, "") if isinstance(source_file, str) else ""
        quote = item.get("source_quote")
        if not isinstance(quote, str) or not quote.strip() or quote not in source or not item.get("event_mapping"):
            errors.append(f"{label} 缺少有效源事件引文与镜头对应说明")
        if not item.get("state_interfaces") or item.get("status") != "pass":
            errors.append(f"{label} 状态接口依据缺失或未通过")
        defects = item.get("defects")
        if not isinstance(defects, list) or any(not isinstance(d, dict) or d.get("status") != "closed" or not d.get("resolution") for d in defects):
            errors.append(f"{label} 缺陷未关闭或未记录复核依据")
    if seen != set(expected) or not expected:
        errors.append("验收记录未覆盖实际交付的全部片段")
    return errors
