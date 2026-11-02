"""可确定检查的片段正文契约。语义与实际生成效果仍由评审判断。"""
from __future__ import annotations

import re
from pathlib import Path

SPEECH = re.compile(r"口型对白|心理独白|画外旁白|画外延续|画外余音|低声自语|混叠人声|(?:对白|台词|独白|旁白|心声)[：:]|说[：:]")
QUOTES = re.compile(r'"[^"\n]*"|“[^”\n]*”|「[^」\n]*」')
CROSS_CLIP = re.compile(
    r"(?:上|下|前|后)(?:一)?(?:个)?(?:片段|段视频|段影片|段)"
    r"|(?:接|承接|衔接)(?:上|前)(?:一)?段|(?:上一|下一)(?:集|章)"
    r"|\b(?:previous|next)\s+(?:clip|segment|episode)\b", re.I)


def instructions_only(prompt: str) -> str:
    prompt = re.sub(r"<d>.*?</d>", "", prompt, flags=re.S)
    lines = []
    for line in prompt.splitlines():
        # 只排除标明为声音的原文对白；给指令加引号不能绕过检查。
        lines.append(QUOTES.sub(
            lambda m: "" if SPEECH.search(line[:m.start()]) else m.group(0), line))
    return "\n".join(lines)


def wan_text_rule() -> str:
    adapter = Path(__file__).resolve().parent.parent / "references" / "wan30-adapter-v1.0.md"
    text = adapter.read_text(encoding="utf-8")
    found = re.search(r"> `(画面文字纪律：[^`\n]+)`", text)
    if not found:
        raise ValueError("Wan3.0 适配器缺少画面文字纪律权威统一句")
    return found[1]


def check(prompt: str, model: str, label: str) -> list[str]:
    errors = []
    cross = CROSS_CLIP.search(instructions_only(prompt))
    if cross:
        errors.append(f"{label}: 视频提示词含跨片段制作说明「{cross[0]}」；正文只写当前片段，衔接记录移至内部")
    if model == "wan30":
        timeline = prompt.split("【时间轴】", 1)[-1].split("【收尾】", 1)[0]
        if SPEECH.search(timeline):
            try:
                sentence = wan_text_rule()
            except (OSError, ValueError) as exc:
                return errors + [f"{label}: {exc}"]
            public = prompt.split("【公共总规范】", 1)[-1].split("【时间轴】", 1)[0]
            public_lines = [line.strip() for line in public.splitlines()]
            if public_lines.count(sentence) != 1 or prompt.count(sentence) != 1:
                errors.append(f"{label}: 含人声的 Wan3.0 片段须在公共总规范独立写一次权威「画面文字纪律：」统一句（TEXT-03）")
    return errors
