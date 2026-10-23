#!/usr/bin/env python3
"""把 Wan3.0 精简制作包迁移到「包内零编号 + 单人塑像图」结构。

- 【参考】块：@ImageN＝CODE 名称（…） → 代码 名称＝职责
- 正文：@ImageN → 代码 名称；角色（@ImageN）： → 角色：
- 角色资产图：场景内单张剧照 → 单人塑像图
"""
import re
import sys
from pathlib import Path

DUTY = {
    "角色": "身份与服装唯一基准（单人塑像图，全片不变）",
    "场景": "空间拓扑与光位基准（全景）",
    "道具": "形制基准（基础态单张）",
}

ASSET_HEAD = re.compile(r"^### (角色|场景|道具) ((?:CHAR|LOC|PROP)_\d+)｜(.+?)\s*$", re.M)


def build_map(text):
    info = {}
    for kind, code, name in ASSET_HEAD.findall(text):
        clean = re.sub(r"（[^）]*）", "", name).strip()
        info[code] = (kind, clean)
    return info


def ref_line(line, info):
    pairs = re.findall(r"@Image(\d+)[＝=]((?:CHAR|LOC|PROP)_\d+)", line)
    if not pairs:
        return line
    order, seen = [], set()
    for _, code in pairs:
        if code not in seen:
            seen.add(code)
            order.append(code)

    def label(code):
        kind, name = info.get(code, ("角色", code))
        return f"{code} {name}＝{DUTY[kind]}"

    tail = ""
    idx = line.find("。参考")
    if idx == -1:
        idx = line.find("。参考仅提供")
    if idx != -1:
        tail = line[idx + 1:]
    else:
        m = re.search(r"参考仅提供.*$", line)
        if m:
            tail = m.group(0)

    body = "【参考】" + "；".join(label(c) for c in order) + "。"

    def sub(m):
        code = m.group(0)
        for n, c in pairs:
            if f"@Image{n}" == code:
                kind, name = info.get(c, ("角色", c))
                return f"{c} {name}"
        return code

    tail = re.sub(r"@Image\d+", sub, tail)
    return body + tail


POSE_OLD = "人物以 3/4 侧身朝向画面外、全身入画、不看镜头，"
POSE_NEW = ("人物正面 3/4 站立，塑像式中性站姿，双臂自然下垂、不摆剧情动作，重心居中；"
            "全身入画、头顶到鞋底完整、脚底齐平，不看镜头，")

FRAME_OLD = "16:9 横版单张电影剧照：不是设定板、不是四视图、不是多视图拼版，画面里只有"
FRAME_NEW = ("16:9 横版单张单人塑像图：单张、单人单身体、中性浅灰无缝背景、塑像式中性站姿、"
             "正面 3/4、全身入画、头顶到鞋底完整、脚底齐平、画面无文字；"
             "不是四视图、不是多视角拼版、不是设定板、不是场景剧照。画面里只有")

BG_OLD = re.compile(r"^场景：LOC_\d+\s+\S.*$", re.M)
BG_NEW = "背景：中性浅灰无缝背景，均匀柔和的顶侧光，脚下极浅的接触阴影；不进场景，不出现建筑、地平线、车辆与陈设。"

LOCK = {
    "阿泽": "阿泽：黑色碎短发／左手腕旧手绳／深灰冲锋衣",
    "苏晚": "苏晚：齐肩黑发／细框银边眼镜／浅白薄冲锋外套",
    "老杨": "老杨：鬓角霜白的利落短发／深色工装夹克／无饰品",
    "许棠": "许棠：高束马尾／黑色机能马甲",
    "小林": "小林：浅棕蓬松软短发／亮蓝防风外套／颈间黑色小相机",
}


def migrate_chunk(chunk, info):
    ref = next((l for l in chunk.split("\n") if l.startswith("【参考】")), None)
    pairs = re.findall(r"@Image(\d+)[＝=]((?:CHAR|LOC|PROP)_\d+)", ref or "")
    mapping = {f"@Image{n}": c for n, c in pairs}

    def sub(m):
        code = mapping.get(m.group(0))
        if not code:
            return m.group(0)
        kind, name = info.get(code, ("角色", code))
        return f"{code} {name}"

    if ref:
        rebuilt = ref_line(ref, info)
        if rebuilt != ref:
            chunk = chunk.replace(ref, rebuilt, 1)
    chunk = re.sub(r"@Image\d+", sub, chunk)
    return chunk


def migrate(text):
    info = build_map(text)
    parts = re.split(r"(```text\n.*?\n```)", text, flags=re.S)
    text = "".join(migrate_chunk(p, info) if p.startswith("```text") else p for p in parts)
    out = []
    for line in text.split("\n"):
        if line.startswith("【参考】"):
            line = ref_line(line, info)
        line = re.sub(r"（@Image\d+）", "", line)
        line = line.replace("以各自 @ImageN 为唯一基准", "以各自参考图为唯一基准")
        line = line.replace(
            "（单张电影剧照：单人、3/4 侧身、场景内、同套剧情服化、方向光、可见皮肤纹理、无文字）",
            "（单人塑像图：单张、单人单身体、中性浅灰无缝背景、全身入画、单色柔光、无文字）")
        line = line.replace("白底四视图仅作内部存档", "四视图仅作内部存档")
        line = line.replace(FRAME_OLD, FRAME_NEW)
        line = BG_OLD.sub(BG_NEW, line)
        line = line.replace(POSE_OLD, POSE_NEW)
        line = line.replace("白底棚拍、纯色背景、", "")
        if "【角色一致性】" in line:
            head, _, rest = line.partition("【角色一致性】")
            seg, sep, tail = rest.partition("【")
            for name, lock in LOCK.items():
                seg = re.sub(
                    rf"{name}(?:（[^）]*）)?[：:][^；。\n]*?(?=；|。)",
                    lock, seg, count=1)
            line = head + "【角色一致性】" + seg + sep + tail
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    new = migrate(src.read_text(encoding="utf-8"))
    if dst:
        dst.write_text(new, encoding="utf-8")
    else:
        sys.stdout.write(new)
    left = re.findall(r"@Image\d+|@图片\d+", new)
    print(f"\n[migrate] 剩余编号 {len(left)} 处", file=sys.stderr)
