#!/usr/bin/env python3
"""batch_ledger.py（批次台账）的回归自测。

运行：python3 scripts/tests/test_batch_ledger.py

覆盖：
  · sync 把 内部/派单/*.manifest.json 登记为「待写」，重复 sync 不重复建账；
  · 标「通过」必须有评审记录、且门须 0 错误（失败关闭）；
  · 草稿在评审后被改 → diagnose 判错（改造四：评审哈希必须等于产物哈希）；
  · 上游文件内容变化 → 判错（批次结论失效）；
  · manifest 的 policy 版本落后 → 提醒（规范漂移，不自动作废）；
  · status 表能渲染出进度行。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ledger = load("batch_ledger")
handoff = load("build_handoff")
continuity = load("continuity_facts")

BRIEF = "# 00 项目输入单\n\n| 项 | 值 |\n|---|---|\n| 生成轨 | wan30 |\n"
TABLE = """# 04 片段规划与逐镜表

## 一、片段 E01-SH01｜开场

场景：LOC_01｜角色：CHAR_01｜道具：PROP_01

| 片段 | 镜 | 起止 | 景别 |
|---|---|---|---|
| SH01 | S01 | 0-3 | 全景 |
"""


def write_facts(tmp: Path) -> Path:
    """真实派生v2骨架并填全状态，保留本批与相邻接口的实际依赖。"""
    facts, path = continuity.init_facts(tmp, None)
    for row in facts['segments']:
        for phase in ('entry', 'exit'):
            row[phase] = {
                'location': 'LOC_01', 'time_of_day': '日', 'light': '左窗自然光',
                'characters': [{'code': 'CHAR_01', 'pos': '门内', 'face': '面向大厅',
                                'costume': '灰色常服', 'injury': '无伤'}],
                'props': [{'code': 'PROP_01', 'state': 'CHAR_01右手持有'}],
            }
    path.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def regenerate_manifest(tmp: Path, segment: str) -> dict:
    card = handoff.build_card(tmp, '4', segment)
    manifest = handoff.build_manifest(tmp, '4', segment, card)
    out = tmp / '内部' / '派单' / f'{segment}.manifest.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def make_project(tmp: Path, segment_count: int = 1) -> Path:
    internal = tmp / "内部"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "00-项目输入单.md").write_text(BRIEF, encoding="utf-8")
    (internal / "03-资产与空间设计.md").write_text("# 资产\n\nCHAR_01｜阿泽\n", encoding="utf-8")
    (internal / "03a-固定资产图片提示词.md").write_text(
        "# 固定资产图片提示词\n\n测试用阶段 2 锁定母版。\n", encoding="utf-8")
    table = '\n\n'.join(TABLE.replace('E01-SH01', f'E01-SH{n:02}').replace(
        '| SH01 |', f'| SH{n:02} |') for n in range(1, segment_count + 1))
    (internal / "04-片段规划与逐镜表.md").write_text(table, encoding="utf-8")
    write_facts(tmp)
    (internal / "04a-片段边界.json").write_text(
        json.dumps({"segments": [{"id": "E01-SH01", "dialogue": [], "action_capacity": []}]}),
        encoding="utf-8")
    (internal / "04b-打斗路由判定表.md").write_text("# 路由\n本批无打斗。\n", encoding="utf-8")
    card = handoff.build_card(tmp, "4", "E01-SH01")
    manifest = handoff.build_manifest(tmp, "4", "E01-SH01", card)
    out = internal / "派单" / "E01-SH01.manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "派单" / "E01-SH01_提示词草稿.md").write_text("草稿正文\n", encoding="utf-8")
    (internal / "05-提示词评审与整改.md").write_text("评审：通过\n", encoding="utf-8")
    return tmp


def do_sync(work: Path):
    """sync 只改内存，落盘才算建账（与 CLI 行为一致）。"""
    data, notes = ledger.sync(work)
    ledger.save_ledger(work, data)
    return data, notes


def batch_id(work: Path) -> str:
    data, _ = do_sync(work)
    return data["batches"][0]["batch_id"]


def scoped_report() -> str:
    return ("# 提示词评审\n评审人：独立评稿 R-01\n共享约束：保持场景窗光方向。\n"
            "总体结论：通过\n未关闭阻断/重要缺陷：0\n\n"
            "## 片段 E01-SH01\n本段证据：角色进门后停步，动作与分镜一致。\n"
            f"| E01-SH01 | {'a' * 64} | 通过 |\n\n"
            "## 片段 E01-SH02\n本段证据：原稿的转身衔接。\n"
            f"| E01-SH02 | {'b' * 64} | 通过 |\n")


def accept_scoped_batch(work: Path):
    bid = batch_id(work)
    draft = work / "内部" / "派单" / "E01-SH01_提示词草稿.md"
    review = work / "内部" / "05-提示词评审与整改.md"
    review.write_text(scoped_report(), encoding="utf-8")
    data, _ = ledger.set_state(work, bid, "通过", draft, review, "0 错误")
    ledger.save_ledger(work, data)
    return bid, draft, review


class LedgerTests(unittest.TestCase):
    def test_continuity_scope_contains_batch_and_immediate_neighbor_only(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), segment_count=4)
            manifest = json.loads((work / '内部/派单/E01-SH01.manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(set(manifest['continuity_upstream']), {'E01-SH01', 'E01-SH02'})
            facts = continuity.load_facts(work / '内部' / continuity.FACTS_NAME)
            board = (work / '内部/04-片段规划与逐镜表.md').read_text(encoding='utf-8')
            self.assertEqual(continuity.check_facts(facts, board, 'storyboard'), ([], []))
            data, _ = do_sync(work)
            self.assertEqual(data['batches'][0]['continuity_upstream'], manifest['continuity_upstream'])

    def test_unrelated_facts_and_top_level_board_hash_preserve_approved_batch(self):
        for changed_index in (2, 3):
            with self.subTest(segment=changed_index + 1), tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d), segment_count=4)
                accept_scoped_batch(work)
                path = work / '内部' / continuity.FACTS_NAME
                facts = json.loads(path.read_text(encoding='utf-8'))
                facts['segments'][changed_index]['entry']['light'] = '其他片段的新灯光'
                facts['upstream']['sha256'] = 'f' * 64
                path.write_text(json.dumps(facts, ensure_ascii=False), encoding='utf-8')
                errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
                self.assertEqual(errors, [])
                regenerate_manifest(work, 'E01-SH01')
                updated, notes = do_sync(work)
                entry = updated['batches'][0]
                self.assertEqual(entry['state'], '通过', notes)
                self.assertIsNotNone(entry['review_sha256'])
                self.assertIsNotNone(entry['reviewed_draft_sha256'])

    def test_neighbor_interface_change_invalidates_approved_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), segment_count=4)
            accept_scoped_batch(work)
            path = work / '内部' / continuity.FACTS_NAME
            facts = json.loads(path.read_text(encoding='utf-8'))
            facts['segments'][1]['entry']['characters'][0]['pos'] = '门外'
            path.write_text(json.dumps(facts, ensure_ascii=False), encoding='utf-8')
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any('衔接事实' in e for e in errors), errors)
            regenerate_manifest(work, 'E01-SH01')
            updated, notes = do_sync(work)
            entry = updated['batches'][0]
            self.assertEqual(entry['state'], '退修', notes)
            self.assertIsNone(entry['review'])
            self.assertIsNone(entry['review_sha256'])
            self.assertIsNone(entry['reviewed_draft_sha256'])
            self.assertIsNone(entry['gate'])

    def test_regenerated_manifests_clear_only_affected_batch_review(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d), segment_count=4)
            regenerate_manifest(work, 'E01-SH04')
            data, _ = do_sync(work)
            for entry in data['batches']:
                segment = entry['segments'][0]
                draft = work / '内部' / '派单' / f'{segment}_提示词草稿.md'
                draft.write_text(f'{segment}正文\n', encoding='utf-8')
                review = work / '内部' / f'05-{segment}-独立评审.md'
                review.write_text('评审：通过\n', encoding='utf-8')
                updated, _ = ledger.set_state(work, entry['batch_id'], '通过', draft, review, '0 错误')
                ledger.save_ledger(work, updated)
            before = {b['segments'][0]: b for b in ledger.load_ledger(work)['batches']}
            path = work / '内部' / continuity.FACTS_NAME
            facts = json.loads(path.read_text(encoding='utf-8'))
            facts['segments'][1]['exit']['characters'][0]['pos'] = '大厅右侧'
            facts['upstream']['sha256'] = 'e' * 64
            path.write_text(json.dumps(facts, ensure_ascii=False), encoding='utf-8')
            regenerate_manifest(work, 'E01-SH01')
            regenerate_manifest(work, 'E01-SH04')
            updated, notes = do_sync(work)
            after = {b['segments'][0]: b for b in updated['batches']}
            self.assertEqual(after['E01-SH01']['state'], '退修', notes)
            self.assertIsNone(after['E01-SH01']['review_sha256'])
            self.assertIsNone(after['E01-SH01']['gate'])
            self.assertEqual(after['E01-SH04']['state'], '通过', notes)
            self.assertEqual(after['E01-SH04']['review_sha256'], before['E01-SH04']['review_sha256'])
            self.assertEqual(after['E01-SH04']['reviewed_draft_sha256'],
                             before['E01-SH04']['reviewed_draft_sha256'])

    def test_sync_registers_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            data, notes = do_sync(work)
            self.assertEqual(len(data["batches"]), 1)
            entry = data["batches"][0]
            self.assertEqual(entry["state"], "待写")
            self.assertEqual(entry["track"], "wan30")
            self.assertEqual(entry["segments"], ["E01-SH01"])
            self.assertTrue(any("登记新批次" in n for n in notes))

    def test_sync_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            do_sync(work)
            data, notes = do_sync(work)
            self.assertEqual(len(data["batches"]), 1)
            self.assertEqual(notes, [])

    def test_pass_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            with self.assertRaises(ValueError) as ctx:
                ledger.set_state(work, bid, "通过", None, None, "0 错误")
            self.assertIn("评审记录", str(ctx.exception))

    def test_pass_rejects_gate_errors(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            with self.assertRaises(ValueError) as ctx:
                ledger.set_state(work, bid, "通过",
                                 work / "内部" / "派单" / "E01-SH01_提示词草稿.md",
                                 work / "内部" / "05-提示词评审与整改.md", "3 错误")
            self.assertIn("0 错误", str(ctx.exception))

    def test_pass_rejects_missing_or_ambiguous_gate(self):
        for gate in (None, "校验完成", "0 错误；3 错误", "0 错误；0 错误"):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d))
                bid = batch_id(work)
                with self.assertRaisesRegex(ValueError, "0 错误"):
                    ledger.set_state(work, bid, "通过",
                                     work / "内部" / "派单" / "E01-SH01_提示词草稿.md",
                                     work / "内部" / "05-提示词评审与整改.md", gate)

    def test_changed_draft_cannot_reuse_same_review(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            draft = work / "内部" / "派单" / "E01-SH01_提示词草稿.md"
            review = work / "内部" / "05-提示词评审与整改.md"
            data, _ = ledger.set_state(work, bid, "通过", draft, review, "0 错误")
            ledger.save_ledger(work, data)
            draft.write_text("修订后的提示词正文\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "旧评审"):
                ledger.set_state(work, bid, "通过", draft, review, "0 错误")

    def test_unrelated_storyboard_segment_change_preserves_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            table = work / "内部" / "04-片段规划与逐镜表.md"
            table.write_text(TABLE + "\n## 二、片段 E01-SH02｜转折\n\n其他段原稿\n", encoding="utf-8")
            card = handoff.build_card(work, "4", "E01-SH01")
            manifest = handoff.build_manifest(work, "4", "E01-SH01", card)
            (work / "内部" / "派单" / "E01-SH01.manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            bid = batch_id(work)
            data, _ = ledger.set_state(work, bid, "通过",
                                      work / "内部" / "派单" / "E01-SH01_提示词草稿.md",
                                      work / "内部" / "05-提示词评审与整改.md", "0 错误")
            ledger.save_ledger(work, data)
            table.write_text(table.read_text(encoding="utf-8").replace("其他段原稿", "其他段已修订"), encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])
            table.write_text(table.read_text(encoding="utf-8").replace("0-3", "0-4"), encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("本批片段已变" in error for error in errors), errors)

    def test_clean_pass_has_no_errors(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            data, _ = ledger.set_state(work, bid, "通过",
                                       work / "内部" / "派单" / "E01-SH01_提示词草稿.md",
                                       work / "内部" / "05-提示词评审与整改.md", "0 错误")
            ledger.save_ledger(work, data)
            errors, warnings = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])
            self.assertEqual([w for w in warnings if "漂移" in w], [])

    def test_draft_changed_after_review_is_error(self):
        """改造四的可执行版本：文件改过而没重评，通过结论必须失效。"""
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            draft = work / "内部" / "派单" / "E01-SH01_提示词草稿.md"
            data, _ = ledger.set_state(work, bid, "通过", draft,
                                       work / "内部" / "05-提示词评审与整改.md", "0 错误")
            ledger.save_ledger(work, data)
            draft.write_text("草稿正文改了一行\n", encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("草稿哈希已变" in e for e in errors), errors)

    def test_stage3_review_hash_is_scoped_to_its_segment_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            table = work / "内部" / "04-片段规划与逐镜表.md"
            table.write_text(TABLE + "\n## 二、片段 E01-SH02｜后续\n\n其他段的内容。\n", encoding="utf-8")
            data, _ = do_sync(work)
            entry = data["batches"][0]
            entry["stage"] = "3"  # This ledger entry models a batch review of the merged 04 file.
            ledger.save_ledger(work, data)
            draft = table
            review = work / "内部" / "04o-阶段3定向复核.md"
            review.write_text("分镜批次复核结论：通过\n打斗路由复核结论：通过\n未关闭阻断/重要缺陷：0\n",
                              encoding="utf-8")
            updated, _ = ledger.set_state(work, entry["batch_id"], "通过", draft, review, "0 错误")
            ledger.save_ledger(work, updated)

            table.write_text(table.read_text(encoding="utf-8").replace("其他段的内容。", "其他段已修改。"),
                              encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])

            table.write_text(table.read_text(encoding="utf-8").replace("0-3", "0-4"), encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("本批分镜片段哈希已变" in e or "上游分镜本批片段已变" in e
                                for e in errors), errors)

    def test_upstream_change_invalidates_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            do_sync(work)
            (work / "内部" / "03-资产与空间设计.md").write_text("# 资产\n\n改过了\n", encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("内容已变" in e for e in errors), errors)

    def test_policy_drift_is_warning(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            data, _ = do_sync(work)
            data["batches"][0]["policy"]["policy_version"] = 1
            ledger.save_ledger(work, data)
            errors, warnings = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("规范已漂移" in w for w in warnings), warnings)

    def test_status_table_renders(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            data, _ = do_sync(work)
            table = ledger.status_table(data)
            self.assertIn("| 批次 | 阶段 | 轨 | 状态 |", table)
            self.assertIn("待写", table)
            self.assertIn("wan30", table)

    def test_scoped_review_ignores_other_segment_changes(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            _, _, review = accept_scoped_batch(work)
            review.write_text(scoped_report().replace("原稿的转身衔接", "已修订的转身衔接"), encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])

    def test_scoped_review_reopens_for_own_evidence_or_shared_changes(self):
        mutations = (("角色进门后停步", "角色进门后坐下"),
                     ("保持场景窗光方向", "改用相反窗光方向"),
                     ("独立评稿 R-01", "独立评稿 R-02"),
                     (f"| E01-SH01 | {'a' * 64} | 通过 |",
                      f"| E01-SH01 | {'a' * 64} | 需修改 |"))
        for old, new in mutations:
            with self.subTest(change=old), tempfile.TemporaryDirectory() as d:
                work = make_project(Path(d))
                _, _, review = accept_scoped_batch(work)
                review.write_text(scoped_report().replace(old, new), encoding="utf-8")
                errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
                self.assertTrue(errors)

    def test_scoped_review_aggregate_changes_do_not_reopen_unchanged_batch(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            _, _, review = accept_scoped_batch(work)
            review.write_text(scoped_report().replace("总体结论：通过", "总体结论：需修改").replace(
                "未关闭阻断/重要缺陷：0", "未关闭阻断/重要缺陷：1"), encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])

    def test_changed_draft_cannot_claim_other_segment_edit_as_new_review(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid, draft, review = accept_scoped_batch(work)
            draft.write_text("本批提示词已经修改。\n", encoding="utf-8")
            review.write_text(scoped_report().replace("原稿的转身衔接", "第二段完成复核"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "旧评审"):
                ledger.set_state(work, bid, "通过", draft, review, "0 错误")

    def test_changed_draft_accepts_updated_own_review_scope(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid, draft, review = accept_scoped_batch(work)
            draft.write_text("本批提示词已经修改。\n", encoding="utf-8")
            review.write_text(scoped_report().replace("角色进门后停步", "角色进门后停步并核对修订正文"),
                              encoding="utf-8")
            data, _ = ledger.set_state(work, bid, "通过", draft, review, "0 错误")
            ledger.save_ledger(work, data)
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertEqual(errors, [])

    def test_legacy_review_retains_whole_file_lock(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            draft = work / "内部" / "派单" / "E01-SH01_提示词草稿.md"
            review = work / "内部" / "05-提示词评审与整改.md"
            data, _ = ledger.set_state(work, bid, "通过", draft, review, "0 错误")
            ledger.save_ledger(work, data)
            review.write_text("评审：通过\n补充一行证据。\n", encoding="utf-8")
            errors, _ = ledger.diagnose(work, ledger.load_ledger(work))
            self.assertTrue(any("评审文件哈希已变" in e for e in errors), errors)

    def test_stage4_rejects_review_index_as_report(self):
        with tempfile.TemporaryDirectory() as d:
            work = make_project(Path(d))
            bid = batch_id(work)
            index = work / "内部" / "05-评审索引.md"
            index.write_text("05a-独立评审.md\n结论：通过\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                ledger.set_state(work, bid, "通过",
                                 work / "内部" / "派单" / "E01-SH01_提示词草稿.md", index, "0 错误")

    def test_fenced_section_examples_do_not_change_scope_membership(self):
        report = scoped_report()
        example = "```markdown\n## 片段 E01-SH99\n示例，不是实际评审。\n```\n"
        first = ledger.wc.review_scope_snapshot(report, ["E01-SH01"])
        # A quoted heading inside the unchanged segment is evidence, not another section.
        updated = report.replace("角色进门后停步", "\n" + example + "角色进门后停步")
        second = ledger.wc.review_scope_snapshot(updated, ["E01-SH01"])
        self.assertNotEqual(first, second)
        peer = ledger.wc.review_scope_snapshot(report, ["E01-SH02"])
        self.assertEqual(peer, ledger.wc.review_scope_snapshot(updated, ["E01-SH02"]))

    def test_partial_scoped_report_cannot_silently_downgrade_to_whole_file_lock(self):
        with self.assertRaises(ValueError):
            ledger.wc.review_scope_snapshot(scoped_report(), ["E01-SH01", "E01-SH99"])


if __name__ == "__main__":
    unittest.main()
