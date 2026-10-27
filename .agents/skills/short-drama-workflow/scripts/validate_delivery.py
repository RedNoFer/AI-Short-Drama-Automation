#!/usr/bin/env python3
"""Validate deterministic delivery rules for the short-drama workflow.

Checks the planned clip inventory, prompt length and format, exact timeline,
hard-cut count, shot IDs, and local asset files. It does not judge story,
performance, visual identity, upload state, or generated video.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

HEADINGS = ("【参数】", "【参考】", "【公共总规范】", "【时间轴】", "【收尾】")
SHOT_LINE = re.compile(
    r"^(?P<start>\d+)-(?P<end>\d+)秒"
    r"｜镜头\s+(?P<shot>[A-Za-z0-9-]+)｜(?P<transition>起始|硬切)"
    r"｜(?P<description>.+)$"
)
IMAGE_MARKER = re.compile(r"@Image\s+(\d+)")
ASSET_ID = re.compile(r"^@(CH|SC|PROP)-\d+$")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON 顶层必须是对象")
    return value


def project_file(root: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: 缺少相对文件路径")
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        errors.append(f"{label}: 必须使用作品目录内的相对路径")
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: 文件路径越出作品目录")
        return None
    if not resolved.is_file() or resolved.stat().st_size == 0:
        errors.append(f"{label}: 文件不存在或为空：{candidate}")
        return None
    return resolved


def image_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        pos = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
               0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            while pos < len(data) and data[pos] == 0xFF:
                pos += 1
            if pos >= len(data):
                break
            marker = data[pos]
            pos += 1
            if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(data):
                break
            size = int.from_bytes(data[pos:pos + 2], "big")
            if size < 2 or pos + size > len(data):
                break
            if marker in sof and size >= 7:
                height = int.from_bytes(data[pos + 3:pos + 5], "big")
                width = int.from_bytes(data[pos + 5:pos + 7], "big")
                return width, height
            pos += size
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        try:
            output = subprocess.check_output(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                text=True, stderr=subprocess.DEVNULL,
            )
            width = re.search(r"pixelWidth:\s*(\d+)", output)
            height = re.search(r"pixelHeight:\s*(\d+)", output)
            if width and height:
                return int(width.group(1)), int(height.group(1))
        except (OSError, subprocess.CalledProcessError):
            pass
    return None


def get_sections(prompt: str, clip_id: str, errors: list[str]) -> dict[str, str] | None:
    positions = []
    for heading in HEADINGS:
        if prompt.count(heading) != 1:
            errors.append(f"{clip_id}: {heading} 必须恰好出现一次")
            return None
        positions.append(prompt.index(heading))
    if positions != sorted(positions):
        errors.append(f"{clip_id}: 五段标题顺序错误")
        return None
    sections = {}
    for index, heading in enumerate(HEADINGS):
        end = positions[index + 1] if index + 1 < len(HEADINGS) else len(prompt)
        sections[heading] = prompt[positions[index] + len(heading):end].strip()
        if not sections[heading]:
            errors.append(f"{clip_id}: {heading} 内容为空")
    return sections


def validate_clip(
    clip: dict, root: Path, assets: dict[str, dict], video_policy: dict,
    errors: list[str],
) -> dict:
    clip_id = clip.get("id")
    if not isinstance(clip_id, str) or not clip_id:
        errors.append("片段缺少 id")
        return {}
    stats = {"id": clip_id}
    model = str(clip.get("model", "")).strip().lower()
    if model not in {"seedance 2.5", "seedance25"}:
        errors.append(
            f"{clip_id}: validate_delivery.py 是旧式 Seedance 2.5 展开包校验器，"
            "不接受缺失或非 Seedance 模型轨；Wan3.0/H3 必须使用 validate_compact_package.py"
        )
        return stats
        return stats
    duration = clip.get("duration_sec")
    default_duration = video_policy["default_duration_sec"]
    if duration != default_duration:
        errors.append(f"{clip_id}: duration_sec 必须为当前策略的 {default_duration} 秒")
    for field in ("ratio", "resolution", "audio", "model"):
        if not isinstance(clip.get(field), str) or not clip[field].strip():
            errors.append(f"{clip_id}: 缺少 {field}")
    prompt_path = project_file(root, clip.get("prompt_path"), f"{clip_id} 提示词", errors)
    if prompt_path is None:
        return stats
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except UnicodeError:
        errors.append(f"{clip_id}: 提示词必须是 UTF-8 文本")
        return stats
    chars = len(prompt)
    stats["characters"] = chars
    if chars > video_policy["prompt_max_chars"]:
        errors.append(
            f"{clip_id}: 提示词 {chars} 字符，超过 {video_policy['prompt_max_chars']}"
        )
    sections = get_sections(prompt, clip_id, errors)
    if sections is None:
        return stats
    parameters = sections["【参数】"]
    for value, label in (
        (clip_id, "片段 ID"),
        (f"{duration}秒", "时长"),
        (clip.get("ratio"), "画幅"),
        (clip.get("resolution"), "清晰度"),
        (clip.get("audio"), "声音"),
        (clip.get("model"), "模型"),
    ):
        if isinstance(value, str) and value not in parameters:
            errors.append(f"{clip_id}: 【参数】缺少{label} {value}")

    expected_shots = clip.get("expected_shot_ids")
    if not isinstance(expected_shots, list) or not expected_shots or not all(
        isinstance(item, str) and item for item in expected_shots
    ):
        errors.append(f"{clip_id}: expected_shot_ids 必须是非空镜头 ID 列表")
        expected_shots = []
    if len(expected_shots) != len(set(expected_shots)):
        errors.append(f"{clip_id}: expected_shot_ids 有重复编号")

    rows = []
    for raw in sections["【时间轴】"].splitlines():
        line = raw.strip()
        if not line:
            continue
        match = SHOT_LINE.fullmatch(line)
        if not match:
            errors.append(f"{clip_id}: 无法解析镜头行（时间必须为整数秒）：{line[:80]}")
            continue
        rows.append(match)
    if not rows:
        errors.append(f"{clip_id}: 【时间轴】没有可解析的镜头")
        return stats
    parsed_shots = [row["shot"] for row in rows]
    stats["shots"] = len(rows)
    if parsed_shots != expected_shots:
        errors.append(f"{clip_id}: 正文镜头 ID/顺序与 expected_shot_ids 不一致")
    if len(parsed_shots) != len(set(parsed_shots)):
        errors.append(f"{clip_id}: 正文镜头 ID 重复")
    cuts = sum(row["transition"] == "硬切" for row in rows)
    stats["hard_cuts"] = cuts
    if rows[0]["transition"] != "起始":
        errors.append(f"{clip_id}: 首镜必须标「起始」")
    if any(row["transition"] != "硬切" for row in rows[1:]):
        errors.append(f"{clip_id}: 首镜之后每镜必须标「硬切」")
    if cuts != len(rows) - 1:
        errors.append(f"{clip_id}: 硬切数必须等于镜头数减一")
    low = video_policy["hard_cuts_min"]
    high = video_policy["hard_cuts_max"]
    if not low <= cuts <= high:
        errors.append(f"{clip_id}: 硬切 {cuts} 次，不在 {low}–{high} 次范围")
    if clip.get("planned_hard_cuts") != cuts:
        errors.append(f"{clip_id}: 实际硬切数与 planned_hard_cuts 不一致")

    previous_end = 0
    for index, row in enumerate(rows, 1):
        start = int(row["start"])
        end = int(row["end"])
        if start != previous_end:
            errors.append(
                f"{clip_id}: 镜头 {index} 从 {start} 秒开始，应从 {previous_end} 秒开始"
            )
        if end <= start:
            errors.append(f"{clip_id}: 镜头 {index} 起止时间无效")
        previous_end = end
    if previous_end != default_duration:
        errors.append(
            f"{clip_id}: 时间轴止于 {previous_end} 秒，应止于 {default_duration} 秒"
        )

    required_assets = clip.get("required_asset_ids")
    references = clip.get("references")
    if (not isinstance(required_assets, list) or not required_assets or not all(
        isinstance(item, str) and ASSET_ID.fullmatch(item)
        for item in required_assets
    )):
        errors.append(f"{clip_id}: required_asset_ids 必须列出本片段可见资产")
        required_assets = []
    if not isinstance(references, list):
        errors.append(f"{clip_id}: references 必须是图片映射列表")
        references = []
    if len(required_assets) != len(set(required_assets)):
        errors.append(f"{clip_id}: required_asset_ids 有重复")
    mapped_assets = []
    mapped_numbers = []
    for ref in references:
        if not isinstance(ref, dict):
            errors.append(f"{clip_id}: 图片映射必须是对象")
            continue
        marker = ref.get("marker")
        asset_id = ref.get("asset_id")
        marker_match = (
            re.fullmatch(r"@Image\s+(\d+)", marker)
            if isinstance(marker, str) else None
        )
        if not marker_match:
            errors.append(f"{clip_id}: 图片编号无效：{marker}")
            continue
        if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
            errors.append(f"{clip_id}: 图片映射资产 ID 无效：{asset_id}")
            continue
        number = int(marker_match.group(1))
        mapped_numbers.append(number)
        mapped_assets.append(asset_id)
        if asset_id not in assets:
            errors.append(f"{clip_id}: 图片映射资产不存在：{asset_id}")
        pattern = re.compile(
            rf"@Image\s+{number}\s*=\s*{re.escape(asset_id)}(?![A-Za-z0-9-])"
        )
        if not pattern.search(sections["【参考】"]):
            errors.append(f"{clip_id}: 【参考】未写明 @Image {number}={asset_id}")
    if mapped_numbers != list(range(1, len(mapped_numbers) + 1)):
        errors.append(f"{clip_id}: @Image 编号必须从 1 连续按上传顺序排列")
    if len(mapped_assets) != len(set(mapped_assets)):
        errors.append(f"{clip_id}: 同一资产重复映射多个 @Image 编号")
    if set(mapped_assets) != set(required_assets):
        errors.append(f"{clip_id}: required_asset_ids 与图片映射资产不一致")
    used_numbers = {int(item) for item in IMAGE_MARKER.findall(prompt)}
    if used_numbers != set(mapped_numbers):
        errors.append(f"{clip_id}: 正文 @Image 编号与机检清单不一致")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="短剧提示词与交付硬性条件校验")
    parser.add_argument("--manifest", required=True, type=Path, help="作品的 00-机检清单.json")
    parser.add_argument("--clip-id", help="仅校验一个片段，用于增量工作")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()
    errors: list[str] = []
    manifest_path = args.manifest.expanduser().resolve()
    policy_path = Path(__file__).resolve().parent.parent / "policy.json"
    try:
        manifest = load_json(manifest_path)
        policy = load_json(policy_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"无法读取清单或策略：{exc}", file=sys.stderr)
        return 2
    root = manifest_path.parent
    if manifest.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    if manifest.get("policy_version") != policy.get("policy_version"):
        errors.append("policy_version 与当前 policy.json 不一致")
    video_policy = policy.get("video", {})
    if not isinstance(video_policy, dict):
        print("policy.json video 必须是对象", file=sys.stderr)
        return 2
    required_policy = (
        "default_duration_sec", "hard_cuts_min", "hard_cuts_max", "prompt_max_chars"
    )
    if any(
        not isinstance(video_policy.get(key), int) or video_policy[key] <= 0
        for key in required_policy
    ) or video_policy["hard_cuts_min"] > video_policy["hard_cuts_max"]:
        print("policy.json 视频规则无效", file=sys.stderr)
        return 2
    asset_policy = policy.get("assets", {})
    if not isinstance(asset_policy, dict):
        print("policy.json assets 必须是对象", file=sys.stderr)
        return 2
    for key in ("character_ratio", "scene_ratio"):
        value = asset_policy.get(key)
        if (not isinstance(value, str) or not re.fullmatch(r"\d+:\d+", value)
                or any(int(part) <= 0 for part in value.split(":"))):
            print(f"policy.json {key} 无效", file=sys.stderr)
            return 2

    clips_raw = manifest.get("clips")
    if not isinstance(clips_raw, list):
        errors.append("clips 必须是列表")
        clips_raw = []
    clips = [clip for clip in clips_raw if isinstance(clip, dict)]
    if len(clips) != len(clips_raw):
        errors.append("clips 中有非对象条目")
    if args.clip_id:
        incremental_assets = set()
        for clip in clips:
            if clip.get("id") == args.clip_id:
                required = clip.get("required_asset_ids")
                if isinstance(required, list):
                    incremental_assets.update(
                        item for item in required if isinstance(item, str)
                    )
    else:
        incremental_assets = None

    assets_raw = manifest.get("assets")
    if not isinstance(assets_raw, list):
        errors.append("assets 必须是列表")
        assets_raw = []
    assets: dict[str, dict] = {}
    for asset in assets_raw:
        if not isinstance(asset, dict):
            errors.append("资产记录必须是对象")
            continue
        asset_id = asset.get("id")
        asset_type = asset.get("type")
        if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
            errors.append(f"资产 ID 无效：{asset_id}")
            continue
        if asset_id in assets:
            errors.append(f"资产 ID 重复：{asset_id}")
        assets[asset_id] = asset
        expected_type = {"CH": "character", "SC": "scene", "PROP": "prop"}[
            asset_id.split("-")[0][1:]
        ]
        if asset_type != expected_type:
            errors.append(f"{asset_id}: type 应为 {expected_type}")
        if incremental_assets is not None and asset_id not in incremental_assets:
            continue
        image_path = project_file(root, asset.get("path"), f"{asset_id} 资产图", errors)
        if image_path is None:
            continue
        dimensions = image_dimensions(image_path)
        if dimensions is None:
            errors.append(f"{asset_id}: 文件不是可识别图片，请使用 PNG/JPEG 或可识别的 WebP")
            continue
        if asset_type in ("character", "scene"):
            width, height = dimensions
            target = asset_policy[f"{asset_type}_ratio"]
            numerator, denominator = (int(part) for part in target.split(":"))
            if height == 0 or denominator == 0 or abs(width / height - numerator / denominator) > 0.02:
                errors.append(f"{asset_id}: 图片为 {width}×{height}，不符合 {target} 画幅")
    planned = manifest.get("planned_clip_ids")
    if not isinstance(planned, list) or not planned or not all(
        isinstance(item, str) and item for item in planned
    ):
        errors.append("planned_clip_ids 必须是非空片段 ID 列表")
        planned = []
    if len(planned) != len(set(planned)):
        errors.append("planned_clip_ids 有重复")
    clip_ids = []
    for clip in clips:
        clip_id = clip.get("id")
        if not isinstance(clip_id, str) or not clip_id:
            errors.append(f"clips 中片段 ID 无效：{clip_id}")
            continue
        clip_ids.append(clip_id)
    if len(clip_ids) != len(set(clip_ids)):
        errors.append("clips 中片段 ID 重复")
    if set(planned) != set(clip_ids):
        errors.append("planned_clip_ids 与 clips 的 ID 集合不一致")
    if args.clip_id:
        selected = [clip for clip in clips if clip.get("id") == args.clip_id]
        if not selected:
            errors.append(f"找不到片段：{args.clip_id}")
    else:
        selected = clips
    stats = [
        validate_clip(clip, root, assets, video_policy, errors) for clip in selected
    ]
    result = {
        "ok": not errors,
        "checked_clips": len(selected),
        "stats": stats,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"硬性校验：{'通过' if result['ok'] else '失败'}；检查 {len(selected)} 条片段")
        for item in stats:
            if item:
                print(
                    f"  {item.get('id')}: {item.get('characters', '?')} 字符，"
                    f"{item.get('shots', '?')} 镜，{item.get('hard_cuts', '?')} 次硬切"
                )
        for item in errors:
            print(f"  错误：{item}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

