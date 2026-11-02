#!/usr/bin/env python3
"""离线核对 Wan3.0 API 请求及附带时长信息；不读取或提交媒体。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "references" / "wan30-official-data.json"


def _finite_number(value) -> bool:
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def check_request(request: dict, media_info: dict | None = None,
                  package: bool = False) -> dict:
    """只检验官方快照已登记字段；media_info 不属于 API 请求。"""
    errors, warnings = [], []
    result = {
        "errors": errors, "warnings": warnings,
        "scope": {
            "kind": "offline_request_metadata_check",
            "data_source": str(DATA_PATH),
            "package_character_limit": package,
            "checked": ["请求字段与类型", "提示词字符数", "素材数量与组合", "声明的时长和输出参数"],
            "not_checked": ["媒体可访问性、上传和解码", "真实文件时长、字节、像素和帧率", "内容语义与生成效果", "供应商实际返回与智能时长"],
            "video_duration_budget_verified": False,
        },
    }
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"无法读取官方规格数据：{exc}")
        return result
    result["scope"]["checked_on"] = data["checked_on"]
    if not isinstance(request, dict):
        errors.append("request 必须是 JSON 对象")
        return result
    if media_info is None:
        media_info = {}
    if not isinstance(media_info, dict):
        errors.append("media_info 必须是以 media 零基索引字符串为键的对象")
        media_info = {}

    def unknown_fields(obj: dict, names: set, path: str):
        unknown = sorted(str(key) for key in obj if key not in names)
        if unknown:
            warnings.append(f"{path} 未检查的字段：{', '.join(unknown)}")

    unknown_fields(request, {"model", "input", "parameters"}, "request")
    if request.get("model") not in data["models"]:
        errors.append(f"model 必须是 {data['models']}")
    inputs = request.get("input")
    if not isinstance(inputs, dict):
        errors.append("input 必须是对象")
        inputs = {}
    unknown_fields(inputs, {"prompt", "media"}, "input")
    prompt = inputs.get("prompt")
    if "prompt" in inputs and not isinstance(prompt, str):
        errors.append("input.prompt 提供时必须是字符串")
    if isinstance(prompt, str):
        if len(prompt) > data["prompt_max_chars"]:
            errors.append(f"input.prompt 超过官方 {data['prompt_max_chars']} 字符上限")
        if package:
            try:
                policy = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
                cap = policy["model_profiles"]["wan30"]["prompt_max_chars"]
                if type(cap) is not int or cap <= 0:
                    raise ValueError("Wan3.0 本地字符上限必须是正整数")
                result["scope"]["package_max_chars"] = cap
                if len(prompt) > cap:
                    errors.append(f"input.prompt 超过本地制作包 {cap} 字符上限")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"无法核对本地制作包字符上限：{exc}")

    parameters = request.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append("parameters 必须是对象")
        parameters = {}
    unknown_fields(parameters, {"duration", "resolution", "ratio", "audio", "prompt_extend"}, "parameters")
    output = data["output"]
    for name, default, choices in (
        ("resolution", output["default_resolution"], output["resolutions"]),
        ("ratio", output["default_ratio"], output["ratios"]),
    ):
        value = parameters.get(name, default)
        if value not in choices:
            errors.append(f"parameters.{name} 必须是 {choices}")
    for name, default in (("audio", output["audio_default"]),
                          ("prompt_extend", data["prompt_extend_default"])):
        if type(parameters.get(name, default)) is not bool:
            errors.append(f"parameters.{name} 必须是布尔值")

    limits = data["media_limits"]
    counts = {kind: 0 for kind in limits}
    totals = {"reference_video": 0.0, "reference_audio": 0.0}
    complete = {kind: True for kind in totals}
    media = inputs.get("media", [])
    if not isinstance(media, list):
        errors.append("input.media 必须是数组")
        media = []
    timed_indices = set()
    valid_media_content = False
    for index, item in enumerate(media):
        label = f"input.media[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象")
            continue
        unknown_fields(item, {"type", "url"}, label)
        kind = item.get("type")
        if not isinstance(kind, str) or kind not in limits:
            errors.append(f"{label}.type 不在官方已登记素材类型内")
            continue
        counts[kind] += 1
        if not isinstance(item.get("url"), str) or not item["url"].strip():
            errors.append(f"{label}.url 必须是非空字符串（可访问性尚未检查）")
        else:
            valid_media_content = True
        if kind not in totals:
            continue
        timed_indices.add(str(index))
        info = media_info.get(str(index))
        seconds = info.get("duration_seconds") if isinstance(info, dict) else None
        if not _finite_number(seconds) or seconds <= 0:
            complete[kind] = False
            errors.append(f"{label} 未完成时长验证：media_info['{index}'].duration_seconds 须为有限正数，不能使用布尔值")
            continue
        rule = limits[kind]
        if not rule["single_min_seconds"] <= seconds <= rule["single_max_seconds"]:
            errors.append(f"{label} 单个时长须在 {rule['single_min_seconds']}–{rule['single_max_seconds']} 秒")
            complete[kind] = False
            continue
        totals[kind] += seconds
    if not (isinstance(prompt, str) and prompt.strip()) and not valid_media_content:
        errors.append("input.prompt 与有效 input.media 至少提供一项；素材须包含合法 type 和非空 url")
    unused_info = sorted(str(key) for key in media_info if key not in timed_indices)
    if unused_info:
        warnings.append("media_info 未使用的索引：" + ", ".join(unused_info))
    for kind, count in counts.items():
        if count > limits[kind]["max_count"]:
            errors.append(f"{kind} 数量 {count} 超过 {limits[kind]['max_count']}")
    for kind, total in totals.items():
        if total > limits[kind]["total_max_seconds"]:
            errors.append(f"{kind} 总时长 {total:g} 秒超过 {limits[kind]['total_max_seconds']} 秒")

    combinations = data["media_combinations"]
    if (combinations["frames_exclude_references"]
            and any(counts[k] for k in combinations["frame_types"])
            and any(counts[k] for k in combinations["reference_types"])):
        errors.append("首尾帧模式与参考输入互斥")
    if (combinations["last_frame_requires_first_frame"]
            and counts["last_frame"] and not counts["first_frame"]):
        errors.append("last_frame 需要 first_frame")
    if counts["file"] + counts["link"] > combinations["file_link_combined_max_count"]:
        errors.append("file 与 link 合计最多一个，二选一")
    if (data["file_or_link_requires_prompt_extend"] and (counts["file"] or counts["link"])
            and parameters.get("prompt_extend", data["prompt_extend_default"]) is False):
        errors.append("file/link 输入需要 prompt_extend=true")

    duration_rule = data["duration"]
    duration = parameters.get("duration", duration_rule["default_seconds"])
    has_video = counts["reference_video"] > 0
    valid_duration = type(duration) is int
    smart = valid_duration and duration == duration_rule["smart_value"]
    if not valid_duration:
        errors.append("parameters.duration 必须是整数秒或 -1，不能使用布尔值")
    elif smart:
        warnings.append("智能时长 -1 已接受：实际输出时长需由平台确认；尚未完成输入视频加输出时长预算验证")
    elif has_video:
        if duration <= 0:
            errors.append("有视频输入时 parameters.duration 须为正整数秒或 -1")
        elif complete["reference_video"]:
            maximum = duration_rule["input_video_plus_output_max_seconds"]
            if duration > maximum - totals["reference_video"]:
                errors.append(f"输入视频加输出时长超过 {maximum} 秒（输入 {totals['reference_video']:g} 秒，输出 {duration} 秒）")
            else:
                result["scope"]["video_duration_budget_verified"] = True
    elif not duration_rule["no_video_min_seconds"] <= duration <= duration_rule["no_video_max_seconds"]:
        errors.append(f"无视频输入时 parameters.duration 须为 {duration_rule['no_video_min_seconds']}–{duration_rule['no_video_max_seconds']} 整数秒或 -1")
    result["scope"]["duration_seconds"] = duration if valid_duration else None
    result["scope"]["media_counts"] = counts
    result["scope"]["declared_media_seconds"] = {
        kind: total if complete[kind] else None for kind, total in totals.items()
    }
    result["ok"] = not errors
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--media-info", type=Path, help="独立 JSON：零基 media 索引到 duration_seconds")
    parser.add_argument("--package", action="store_true", help="额外核对本地制作包字符上限；不检查制作包四段语法")
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        info = json.loads(args.media_info.read_text(encoding="utf-8")) if args.media_info else None
    except (OSError, ValueError) as exc:
        result = {"errors": [f"无法读取 JSON：{exc}"], "warnings": [],
                  "scope": {"kind": "offline_request_metadata_check", "checked": [], "not_checked": ["请求内容，JSON读取失败"]}}
    else:
        result = check_request(request, info, args.package)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
