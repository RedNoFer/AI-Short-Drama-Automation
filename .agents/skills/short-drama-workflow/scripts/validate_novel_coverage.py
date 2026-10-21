#!/usr/bin/env python3
"""校验精简制作包各集「小说原文」块对用户指定源小说的逐字覆盖率。

用途：小说原文块必须逐字来自用户提供的源文件，不得在改编中被悄悄改写或漏分配。
源文件支持 .txt/.md 与 .docx（stdlib 直读，不依赖第三方库）。源小说只覆盖部分
章节时用 --allow-partial；阈值可用参数调整。机检只证明文字覆盖，剧情取舍仍由
agent 按 story-evaluation 判断。
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NOVEL_BLOCK = re.compile(r"## 剧集\s+(?P<ep>[A-Za-z0-9_-]+)[^\n]*\n.*?### 小说原文\s*\n```(?:text)?\s*\n(?P<body>.*?)```", re.S)


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.iter(f"{{{ns['w']}}}p"):
        text = "".join(node.text or "" for node in para.iter(f"{{{ns['w']}}}t"))
        paragraphs.append(text)
    return "\n".join(paragraphs)


def read_source(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return read_docx(path)
    return path.read_text(encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验制作包小说原文块对源小说的逐字覆盖率")
    parser.add_argument("package", type=Path, help="精简制作包 Markdown")
    parser.add_argument("source", type=Path, help="用户提供的源小说（txt/md/docx），以输入单登记的版本为准")
    parser.add_argument("--min-md-hit", type=float, default=0.99,
                        help="MD 原文块须在源中逐字命中的比例下限（默认 0.99）")
    parser.add_argument("--min-source-coverage", type=float, default=0.95,
                        help="源小说被各集原文块覆盖的比例下限（默认 0.95；只制作部分章节时用 --allow-partial）")
    parser.add_argument("--allow-partial", action="store_true",
                        help="源小说允许只覆盖部分章节（不校验源覆盖率，只报告）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    md = args.package.read_text(encoding="utf-8")
    blocks = [(m["ep"], m["body"]) for m in NOVEL_BLOCK.finditer(md)]
    if not blocks:
        print("未解析到任何「### 小说原文」块", file=sys.stderr)
        return 2
    source = normalize(read_source(args.source))
    md_text = normalize("".join(body for _, body in blocks))

    matcher = difflib.SequenceMatcher(None, source, md_text, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    md_hit = matched / len(md_text) if md_text else 0.0
    coverage = matched / len(source) if source else 0.0

    diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        diffs.append({
            "type": {"replace": "改写", "delete": "源文未分配", "insert": "块内新增(源中无)"}[tag],
            "source": source[max(0, i1 - 12):i2 + 12],
            "package": md_text[max(0, j1 - 12):j2 + 12],
        })

    errors = []
    if md_hit < args.min_md_hit:
        errors.append(f"原文块逐字命中率 {md_hit:.4f} 低于 {args.min_md_hit}：存在改写，须恢复逐字或在输入单登记改编授权")
    if not args.allow_partial and coverage < args.min_source_coverage:
        errors.append(f"源小说覆盖率 {coverage:.4f} 低于 {args.min_source_coverage}：部分章节未分配进任何集；只制作部分章节须传 --allow-partial 并在输入单注明范围")

    if args.json:
        import json
        print(json.dumps({"episodes": len(blocks), "md_chars": len(md_text), "source_chars": len(source),
                          "md_hit_ratio": round(md_hit, 4), "source_coverage": round(coverage, 4),
                          "differences": diffs, "ok": not errors}, ensure_ascii=False, indent=2))
    else:
        print(f"小说原文覆盖：{'通过' if not errors else '失败'}；{len(blocks)} 集、块内 {len(md_text)} 字、源 {len(source)} 字")
        print(f"  原文块逐字命中率：{md_hit:.4f}（下限 {args.min_md_hit}）")
        print(f"  源小说覆盖率：{coverage:.4f}（下限 {args.min_source_coverage}，部分章节模式：{args.allow_partial}）")
        for index, item in enumerate(diffs[:20], 1):
            print(f"  差异{index} [{item['type']}] 源：{item['source']}")
            print(f"            包内：{item['package']}")
        if len(diffs) > 20:
            print(f"  另有 {len(diffs) - 20} 处差异，用 --json 查看")
        for item in errors:
            print(f"  错误：{item}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
