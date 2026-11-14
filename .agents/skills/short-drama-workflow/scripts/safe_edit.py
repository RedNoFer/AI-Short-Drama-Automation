#!/usr/bin/env python3
"""包文件安全编辑器 — 防多写者互踩(2026-11-14 并行覆盖事故的系统性解决)。

任何对精简制作包等交付文件的修改,必须经此工具:
  写前:基线SHA校验(文件被别人动过→拒绝,先diff)+写锁(本地单写者,180分钟过期)
  写中:编辑函数只做纯文本变换
  写后:时间戳备份→机检(exit=0才落盘)→原子写→更新基线→释放锁

库用法:
    from safe_edit import PackageEditor
    ed = PackageEditor.begin(pkg, model="wan30", note="一句话说明")
    new = ed.content.replace("a", "b")     # 纯文本变换
    ed.commit(new)

CLI 用法:
    python3 safe_edit.py <包.md> --check           # 当前SHA vs 基线 + 锁状态
    python3 safe_edit.py <包.md> --set-baseline    # 把当前SHA记为基线(diff确认后用)
    python3 safe_edit.py <包.md> --patch 脚本.py   # 脚本须定义 apply(content)->str
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

LOCK_STALE_MIN = 180
GATE = Path(__file__).resolve().parent / "validate_compact_package.py"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _side_files(pkg: Path) -> dict:
    return {
        "baseline": pkg.with_suffix(pkg.suffix + ".baseline"),
        "lock": pkg.with_suffix(pkg.suffix + ".lock.json"),
    }


def _read_sha(path: Path) -> str:
    return sha256_of(path.read_bytes())


class LockedByOther(RuntimeError):
    pass


class BaselineDrift(RuntimeError):
    pass


class GateFailed(RuntimeError):
    pass


class PackageEditor:
    def __init__(self, pkg: Path, model: str = "wan30", note: str = "",
                 force: bool = False, space_exempt: bool = False):
        self.pkg = Path(pkg)
        self.model = model
        self.note = note or "未注明"
        self.force = force
        self.space_exempt = space_exempt
        self.side = _side_files(self.pkg)
        self.raw = self.pkg.read_bytes()
        self.sha_before = _read_sha(self.pkg)
        self.content = self.raw.decode("utf-8")
        self._lock_acquired = False

    # —— 写前 ——
    def begin(self) -> "PackageEditor":
        self._check_lock()
        self._acquire_lock()
        base = self.side["baseline"]
        if base.exists() and not self.force:
            expected = base.read_text(encoding="utf-8").strip()
            if expected != self.sha_before:
                self._release_lock()
                raise BaselineDrift(
                    f"文件SHA与基线不一致——文件已被其他会话/agent修改!\n"
                    f"  基线: {expected[:16]}…  当前: {self.sha_before[:16]}…\n"
                    f"  处置: 先 diff 弄清差异与来源,确认后 --set-baseline 重设基线再改;\n"
                    f"        绝不能在未知基线上叠加编辑(2026-11-14 并行覆盖事故实证)")
        return self

    def _check_lock(self):
        lock = self.side["lock"]
        if not lock.exists():
            return
        try:
            info = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            lock.unlink()
            return
        since = datetime.fromisoformat(info["since"])
        if datetime.now() - since < timedelta(minutes=LOCK_STALE_MIN):
            if not self.force:
                raise LockedByOther(
                    f"写锁被持有: {info['writer']} 自 {info['since']} 起(任务:{info['note']})。"
                    f" 等其完成或 --force 抢锁;绝不并行编辑同一包")
        else:
            print(f"提示: 过期写锁已自动失效({info['writer']}, {info['since']})")

    def _acquire_lock(self):
        self.side["lock"].write_text(json.dumps({
            "writer": f"{os.uname().nodename}:pid{os.getpid()}",
            "since": datetime.now().isoformat(timespec="seconds"),
            "note": self.note,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        self._lock_acquired = True

    def _release_lock(self):
        if self._lock_acquired and self.side["lock"].exists():
            self.side["lock"].unlink()
            self._lock_acquired = False

    # —— 写后 ——
    def commit(self, new_content: str) -> Path:
        new_bytes = new_content.encode("utf-8")
        if new_bytes == self.raw:
            self._release_lock()
            print("内容无变化,跳过写盘")
            return self.pkg
        # 1) 时间戳备份
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = self.pkg.with_name(self.pkg.name + f".bak-{stamp}")
        bak.write_bytes(self.raw)
        # 2) 机检(临时文件上跑,不合格不落盘)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8", dir=str(self.pkg.parent)) as fh:
            fh.write(new_content)
            tmp = Path(fh.name)
        try:
            gate_cmd = [sys.executable, str(GATE), str(tmp), "--model", self.model]
            if self.space_exempt:
                gate_cmd.append("--space-exempt")
            proc = subprocess.run(gate_cmd, capture_output=True, text=True)
            err_count = sum("错误：" in ln or "错误:" in ln
                            for ln in (proc.stdout + proc.stderr).splitlines())
            if proc.returncode != 0 or err_count:
                print((proc.stdout + proc.stderr)[:3000])
                self._release_lock()
                raise GateFailed(f"机检 {err_count} 个错误——本次编辑不落盘;备份仍在 {bak.name}")
        finally:
            tmp.unlink(missing_ok=True)
        # 3) 原子写 + 权限
        fd, tmp2 = tempfile.mkstemp(dir=str(self.pkg.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        os.chmod(tmp2, 0o644)
        os.replace(tmp2, self.pkg)
        # 4) 更新基线 + 释放锁
        self.side["baseline"].write_text(sha256_of(new_bytes), encoding="utf-8")
        self._release_lock()
        print(f"落盘: {len(self.raw)} → {len(new_bytes)} 字节; 备份 {bak.name}; "
              f"新基线 {sha256_of(new_bytes)[:16]}…; 机检通过")
        return self.pkg


def _cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set-baseline", action="store_true")
    ap.add_argument("--patch", help="定义 apply(content)->str 的 python 脚本")
    ap.add_argument("--model", default="wan30")
    ap.add_argument("--note", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--space-exempt", action="store_true",
                    help="测试沙盒无站位目录时透传给机检")
    args = ap.parse_args()
    pkg = Path(args.pkg)
    side = _side_files(pkg)
    if args.check:
        cur = _read_sha(pkg)
        base = side["baseline"].read_text(encoding="utf-8").strip() if side["baseline"].exists() else "(无基线)"
        ok = "✓" if cur == base else "✗ 已漂移(有其他写者动过)"
        lock = ""
        if side["lock"].exists():
            lock = " 锁:" + side["lock"].read_text(encoding="utf-8").replace("\n", " ")
        print(f"当前 {cur[:16]}… 基线 {base[:16]}… {ok}{lock}")
        return
    if args.set_baseline:
        side["baseline"].write_text(_read_sha(pkg), encoding="utf-8")
        print(f"基线已设为当前 {_read_sha(pkg)[:16]}… (确认过 diff 了吗?)")
        return
    if args.patch:
        ns = {}
        exec(open(args.patch, encoding="utf-8").read(), ns)
        assert callable(ns.get("apply")), "补丁脚本须定义 apply(content)->str"
        ed = PackageEditor(pkg, model=args.model, note=args.note or args.patch,
                           force=args.force,
                           space_exempt=args.space_exempt).begin()
        new = ns["apply"](ed.content)
        ed.commit(new)
        return


if __name__ == "__main__":
    _cli()
