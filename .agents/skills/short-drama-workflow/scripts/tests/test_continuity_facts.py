#!/usr/bin/env python3
"""continuity_facts.py（衔接事实 JSON）的回归自测。

运行：python3 scripts/tests/test_continuity_facts.py

覆盖：
  · --init 从逐镜表派生：片段 ID、逐镜起止、场景→entry.location、角色→entry.characters；
  · 时间轴与正文逐行不一致 → 判错；
  · 入口人物未在【参考】绑定 → 判错；
  · 跨段地点跳变 → 判错；
  · 下一段人物、持物、位置变化须有 handoff_changes 逐项证据；
  · 空时间轴、TODO、缺片段、next跳段及提前终止均失败关闭；
  · 有证据的闪回、放下道具、人物离场可以通过；
  · schema 版本不符 → 失败关闭。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("continuity_facts", ROOT / "scripts" / "continuity_facts.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)

BOARD = """# 04-片段规划与逐镜表

## E01/SH01｜扩音器响在大厅（30 秒 / 3 镜）

场景：LOC_01｜角色：CHAR_01、CHAR_02｜道具：PROP_02

| 镜 | 时间 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 内容要点 | 表演 |
|---|---|---|---|---|---|---|---|---|
| S01 | 0-10 | 全景 | 24mm | 侧45度平视 | 横移 | 深 | 定场 | — |
| S02 | 10-20 | 中景 | 50mm | 侧45度平视 | 推进 | 浅 | 举喇叭 | — |
| S03 | 20-30 | 近景 | 85mm | 俯拍 | 推进 | 浅 | 拍票据 | — |

## E01/SH02｜谈恋爱时一起吃的饭（30 秒 / 3 镜）

场景：LOC_01｜角色：CHAR_01、CHAR_02｜道具：PROP_02

| 镜 | 时间 | 景别 | 焦段 | 机位 | 运镜 | 景深 | 内容要点 | 表演 |
|---|---|---|---|---|---|---|---|---|
| S01 | 0-10 | 近景 | 85mm | 侧45度平视 | 横移 | 浅 | 停步 | — |
| S02 | 10-20 | 中景 | 50mm | 过肩平视 | 推进 | 浅 | 反问 | — |
| S03 | 20-30 | 中景 | 35mm | 侧后方 | 跟拍 | 深 | 穿过缝隙 | — |
"""

BODY = """# 阶段 4 片段骨架

## 剧集 E01

### 片段 E01-SH01｜扩音器响在大厅

#### 参考

CHAR_01＝周凯；CHAR_02＝许妍；LOC_01＝大厅；PROP_02＝票据

#### 视频提示词

```text
【参考】CHAR_01＝周凯；CHAR_02＝许妍；LOC_01＝大厅；PROP_02＝票据
【公共总规范】写实，低饱和
【时间轴】
0-10秒，周凯立中庭举喇叭
10-20秒，硬切，他把票据拍在台面
20-30秒，硬切，前台抬头
【收尾】他转身朝电梯
```

### 片段 E01-SH02｜谈恋爱时一起吃的饭

#### 参考

CHAR_01＝周凯；CHAR_02＝许妍；LOC_01＝大厅；PROP_02＝票据

#### 视频提示词

```text
【参考】CHAR_01＝周凯；CHAR_02＝许妍；LOC_01＝大厅；PROP_02＝票据
【公共总规范】写实，低饱和
【时间轴】
0-10秒，许妍停步
10-20秒，硬切，她反问
20-30秒，硬切，她穿过缝隙
【收尾】她走到电梯口
```
"""


def facts_of(segments: list[dict]) -> dict:
    return {"schema": cf.SCHEMA, "policy": {}, "segments": segments}


def seg(sid: str, nxt: str | None, loc="LOC_01", chars=("CHAR_01", "CHAR_02"),
        props=None, exit_chars=None, exit_props=None) -> dict:
    shots = [{"no": "S01", "start": 0, "end": 10},
             {"no": "S02", "start": 10, "end": 20},
             {"no": "S03", "start": 20, "end": 30}]
    return {
        "id": sid,
        "shots": shots,
        "entry": {
            "location": loc,
            "time_of_day": "日",
            "light": "左窗自然光",
            "characters": [{"code": c, "pos": "中庭", "face": "面向前台",
                            "costume": "灰色常服", "injury": "无伤"} for c in chars],
            "props": props if props is not None else [{"code": "PROP_02", "state": "在台面"}],
        },
        "exit": {
            "location": loc,
            "time_of_day": "日",
            "light": "左窗自然光",
            "characters": [{"code": c, "pos": "中庭", "face": "面向前台",
                            "costume": "灰色常服", "injury": "无伤"}
                           for c in (exit_chars if exit_chars is not None else chars)],
            "props": exit_props if exit_props is not None else [{"code": "PROP_02", "state": "在台面"}],
        },
        "next": nxt,
        "transition": {"type": "continuous"},
        "handoff_changes": [],
    }


class ContinuityTests(unittest.TestCase):
    def test_init_from_storyboard(self):
        with tempfile.TemporaryDirectory() as d:
            internal = Path(d) / "内部"
            internal.mkdir()
            (internal / "04-片段规划与逐镜表.md").write_text(BOARD, encoding="utf-8")
            data, path = cf.init_facts(Path(d), "E01-SH01~SH02")
            self.assertEqual([s["id"] for s in data["segments"]], ["E01-SH01", "E01-SH02"])
            first = data["segments"][0]
            self.assertEqual(first["entry"]["location"], "LOC_01")
            self.assertEqual([c["code"] for c in first["entry"]["characters"]], ["CHAR_01", "CHAR_02"])
            self.assertEqual([p["code"] for p in first["entry"]["props"]], ["PROP_02"])
            self.assertEqual([s["start"] for s in first["shots"]], [0, 10, 20])
            self.assertEqual(first["next"], "E01-SH02")
            self.assertIsNone(data["segments"][1]["next"])
            self.assertEqual(path.name, "04c-衔接事实.json")

    def test_consistent_facts_pass(self):
        errors, warnings = cf.check_facts(
            facts_of([seg("E01-SH01", "E01-SH02"), seg("E01-SH02", None)]), BODY)
        self.assertEqual(errors, [])

    def test_timeline_mismatch_is_error(self):
        facts = facts_of([seg("E01-SH01", "E01-SH02"), seg("E01-SH02", None)])
        facts["segments"][0]["shots"][1]["start"] = 11
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any("时间轴与衔接事实不一致" in e for e in errors), errors)

    def test_unbound_character_is_error(self):
        facts = facts_of([seg("E01-SH01", "E01-SH02", chars=("CHAR_01", "CHAR_09")),
                          seg("E01-SH02", None)])
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any("CHAR_09" in e and "未在正文【参考】绑定" in e for e in errors), errors)

    def test_location_jump_is_error(self):
        facts = facts_of([seg("E01-SH01", "E01-SH02", loc="LOC_01"),
                          seg("E01-SH02", None, loc="LOC_02")])
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any("地点跳变" in e for e in errors), errors)

    def test_ghost_character_is_error(self):
        facts = facts_of([seg("E01-SH01", "E01-SH02", chars=("CHAR_01", "CHAR_02"),
                              exit_chars=("CHAR_01",)),
                          seg("E01-SH02", None, chars=("CHAR_01", "CHAR_02"))])
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any("凭空出现" in e for e in errors), errors)

    def test_arrival_with_evidence_on_following_segment_passes(self):
        facts = facts_of([seg("E01-SH01", "E01-SH02", chars=("CHAR_01", "CHAR_02"),
                              exit_chars=("CHAR_01",)),
                          seg("E01-SH02", None, chars=("CHAR_01", "CHAR_02"))])
        facts['segments'][1]['handoff_changes'] = [
            {'kind': 'arrival', 'code': 'CHAR_02', 'evidence': '分镜SH02/S01：许妍从电梯口走近'}]
        errors, _ = cf.check_facts(facts, BODY)
        self.assertEqual(errors, [])

    def test_prop_chain_break_is_error(self):
        facts = facts_of([
            seg("E01-SH01", "E01-SH02",
                exit_props=[{"code": "PROP_02", "state": "票据握在他手里"}]),
            seg("E01-SH02", None, props=[]),
        ])
        errors, warnings = cf.check_facts(facts, BODY)
        self.assertTrue(any("持物链可能断" in e for e in errors), errors)
        self.assertEqual(warnings, [])

    def test_bad_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "04c-衔接事实.json"
            path.write_text(json.dumps({"schema": "wrong/1", "segments": []}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                cf.load_facts(path)
            self.assertIn("schema", str(ctx.exception))

    def test_body_segment_missing_from_facts_is_error(self):
        facts = facts_of([seg("E01-SH01", None)])
        errors, warnings = cf.check_facts(facts, BODY)
        self.assertTrue(any("正文有该片段" in e for e in errors), errors)
        self.assertEqual(warnings, [])

    def test_empty_fact_or_source_timeline_is_error(self):
        for empty_fact in (True, False):
            facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
            source = BODY
            if empty_fact:
                facts['segments'][0]['shots'] = []
            else:
                source = BODY.replace('0-10秒，周凯立中庭举喇叭', '').replace(
                    '10-20秒，硬切，他把票据拍在台面', '').replace('20-30秒，硬切，前台抬头', '')
            errors, _ = cf.check_facts(facts, source)
            self.assertTrue(any('缺逐镜时间轴' in e for e in errors), errors)

    def test_todo_and_missing_fields_never_pass(self):
        for phase in ('entry', 'exit'):
            for key in ('location', 'time_of_day', 'light'):
                facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
                facts['segments'][0][phase][key] = 'TODO'
                errors, _ = cf.check_facts(facts, BODY)
                self.assertTrue(any(f'{phase}.{key}' in e for e in errors), errors)
            for group, fields in (('characters', ('code', 'pos', 'face', 'costume', 'injury')),
                                  ('props', ('code', 'state'))):
                for field in fields:
                    facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
                    facts['segments'][0][phase][group][0][field] = 'TODO'
                    errors, _ = cf.check_facts(facts, BODY)
                    self.assertTrue(any(f'{phase}.{group}.{field}' in e for e in errors), errors)

    def test_init_skeleton_cannot_pass_until_filled(self):
        with tempfile.TemporaryDirectory() as d:
            internal = Path(d) / '内部'
            internal.mkdir()
            (internal / '04-片段规划与逐镜表.md').write_text(BOARD, encoding='utf-8')
            facts, _ = cf.init_facts(Path(d), None)
            errors, _ = cf.check_facts(facts, BOARD, 'storyboard')
            self.assertTrue(any('TODO' in e for e in errors), errors)
            self.assertEqual(facts['schema'], 'continuity-facts/2')

    def test_next_cannot_stop_early_or_skip_source_neighbor(self):
        for next_id in (None, 'E01-SH03'):
            facts = facts_of([seg('E01-SH01', next_id), seg('E01-SH02', None)])
            errors, _ = cf.check_facts(facts, BODY)
            self.assertTrue(any('不能跳过接口或提前结束' in e for e in errors), errors)

    def test_next_unknown_target_is_error(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH99'), seg('E01-SH02', None)])
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('next 指向不存在' in e for e in errors), errors)

    def test_next_complex_object_fails_without_crashing(self):
        for invalid in ({'target': 'E01-SH02'}, ['E01-SH02'], True, 2):
            facts = facts_of([seg('E01-SH01', invalid), seg('E01-SH02', None)])
            errors, _ = cf.check_facts(facts, BODY)
            self.assertTrue(errors, invalid)

    def test_top_level_non_object_fails_without_crashing(self):
        for invalid in ([], None, 'facts', 1):
            errors, _ = cf.check_facts(invalid, BODY)
            self.assertTrue(errors, invalid)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / cf.FACTS_NAME
            for invalid in ([], None, 'facts', 1):
                path.write_text(json.dumps(invalid), encoding='utf-8')
                with self.assertRaises(ValueError):
                    cf.load_facts(path)

    def test_transition_defaults_to_continuous(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        for item in facts['segments']:
            item.pop('transition')
        self.assertEqual(cf.check_facts(facts, BODY), ([], []))

    def test_evidenced_flashback_can_change_location_people_and_light(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'),
                          seg('E01-SH02', None, loc='LOC_02', chars=('CHAR_01',))])
        following = facts['segments'][1]
        following['transition'] = {'type': 'flashback', 'reason': '进入周凯回忆',
                                   'evidence': '原文第2段：三年前在旧屋'}
        following['entry']['time_of_day'] = '夜'
        following['entry']['light'] = '旧屋暖灯'
        before, following_source = BODY.split('### 片段 E01-SH02', 1)
        source = before + '### 片段 E01-SH02' + following_source.replace('LOC_01', 'LOC_02')
        errors, warnings = cf.check_facts(facts, source)
        self.assertEqual(errors, [], errors)
        self.assertEqual(warnings, [])

    def test_transition_without_evidence_is_error(self):
        for key in ('reason', 'evidence'):
            facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None, loc='LOC_02')])
            transition = {'type': 'flashback', 'reason': '回忆', 'evidence': '原文第2段'}
            transition[key] = ''
            facts['segments'][1]['transition'] = transition
            errors, _ = cf.check_facts(facts, BODY)
            self.assertTrue(any('有意转场须登记' in e for e in errors), errors)

    def test_old_arrives_without_evidence_cannot_waive_arrival(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02', exit_chars=('CHAR_01',)),
                          seg('E01-SH02', None)])
        facts['segments'][0]['exit']['arrives'] = ['CHAR_02']
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('凭空出现' in e for e in errors), errors)

    def test_handoff_change_on_previous_segment_does_not_waive_next(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02', exit_chars=('CHAR_01',)),
                          seg('E01-SH02', None)])
        facts['segments'][0]['handoff_changes'] = [
            {'kind': 'arrival', 'code': 'CHAR_02', 'evidence': '放错位置的登记'}]
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('凭空出现' in e for e in errors), errors)

    def test_prop_put_down_and_character_departure_need_evidence(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02',
                              exit_props=[{'code': 'PROP_02', 'state': '周凯手持票据'}]),
                          seg('E01-SH02', None, chars=('CHAR_01',), props=[])])
        changes = [{'kind': 'prop', 'code': 'PROP_02', 'evidence': 'SH02/S01：票据留在台面并离画'},
                   {'kind': 'departure', 'code': 'CHAR_02', 'evidence': 'SH02/S01：许妍走出大厅'}]
        facts['segments'][1]['handoff_changes'] = changes
        self.assertEqual(cf.check_facts(facts, BODY), ([], []))
        for item in changes:
            original = item['evidence']
            item['evidence'] = ''
            errors, _ = cf.check_facts(facts, BODY)
            self.assertTrue(any('handoff_changes 缺有效' in e for e in errors), errors)
            item['evidence'] = original

    def test_state_change_without_evidence_blocks(self):
        for field, value, kind in (('pos', '电梯口', 'position'), ('face', '朝向门口', 'position'),
                                   ('costume', '蓝色外套', 'costume'), ('injury', '左手擦伤', 'injury')):
            facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
            facts['segments'][1]['entry']['characters'][0][field] = value
            errors, _ = cf.check_facts(facts, BODY)
            self.assertTrue(any(f'无 {kind} 依据' in e for e in errors), errors)
            facts['segments'][1]['handoff_changes'] = [
                {'kind': kind, 'code': 'CHAR_01', 'evidence': f'分镜SH02/S01明确{field}变化'}]
            self.assertEqual(cf.check_facts(facts, BODY), ([], []))

    def test_prop_state_change_requires_evidence(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        facts['segments'][1]['entry']['props'][0]['state'] = '在周凯手中'
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('无 prop 依据' in e for e in errors), errors)
        facts['segments'][1]['handoff_changes'] = [
            {'kind': 'prop', 'code': 'PROP_02', 'evidence': 'SH02/S01：周凯拿起票据'}]
        self.assertEqual(cf.check_facts(facts, BODY), ([], []))

    def test_malformed_or_codeless_objects_fail_without_crashing(self):
        for phase in ('entry', 'exit'):
            for group in ('characters', 'props'):
                for value in ({}, {'code': {}}, 'CHAR_01'):
                    facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
                    facts['segments'][0][phase][group] = [value]
                    errors, _ = cf.check_facts(facts, BODY)
                    self.assertTrue(errors, (phase, group, value))

    def test_storyboard_time_axis_passes_and_mismatch_blocks(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        self.assertEqual(cf.check_facts(facts, BOARD, 'storyboard'), ([], []))
        facts['segments'][0]['shots'][0]['end'] = 9
        errors, _ = cf.check_facts(facts, BOARD, 'storyboard')
        self.assertTrue(any('时间轴与衔接事实不一致' in e for e in errors), errors)

    def test_compact_package_short_fragment_ids_keep_episode_context(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        source = BODY.replace('## 剧集 E01', '## 剧集 E01｜测试', 1).replace(
            '### 片段 E01-SH', '### 片段 SH')
        self.assertEqual(cf.check_facts(facts, source), ([], []))

    def test_h3_timeline_uses_cut_starts_and_declared_duration(self):
        block = '''### 片段 SH01｜30秒｜H3测试
integrated_multimodal_description: 初始镜头
[Shot 2] At 00:10 第二镜
[Shot 3] At 00:20 第三镜'''
        self.assertEqual(cf.parse_body_timeline(block), [(0, 10), (10, 20), (20, 30)])
        self.assertEqual(cf.parse_body_timeline(block.replace('｜30秒', '')), [])

    def test_h3_source_crosschecks_full_facts(self):
        source = '# 精简制作包\n\n## 剧集 E01｜H3\n\n'
        for number in (1, 2):
            source += f'''### 片段 SH0{number}｜30秒｜H3测试
【参考】CHAR_01＝周凯；CHAR_02＝许妍；LOC_01＝大厅；PROP_02＝票据
integrated_multimodal_description: 初始镜头
[Shot 2] At 00:10 第二镜
[Shot 3] At 00:20 第三镜
'''
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        self.assertEqual(cf.check_facts(facts, source), ([], []))
        errors, _ = cf.check_facts(facts, source.replace('At 00:10', 'At 00:11', 1))
        self.assertTrue(any('时间轴与衔接事实不一致' in e for e in errors), errors)

    def test_h3_single_shot_has_complete_timeline(self):
        self.assertEqual(cf.parse_body_timeline(
            '### 片段 SH01｜30秒｜测试\nintegrated_multimodal_description: [Shot 1] Opening.'),
            [(0, 30)])

    def test_h3_ref2va_timeline_is_supported(self):
        self.assertEqual(cf.parse_body_timeline(
            '### 片段 SH01｜30秒｜测试\ndetailed_description: [Shot 1] Opening.\n'
            '[Shot 2] At 00:15.000, reaction.'), [(0, 15), (15, 30)])

    def test_light_change_requires_evidence_and_time_jump_requires_transition(self):
        facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
        facts['segments'][1]['entry']['light'] = '顶灯开启'
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('光向变化未登记' in e for e in errors), errors)
        facts['segments'][1]['handoff_changes'] = [
            {'kind': 'light', 'code': 'scene', 'evidence': 'SH02/S01：大厅顶灯打开'}]
        self.assertEqual(cf.check_facts(facts, BODY), ([], []))
        facts['segments'][1]['entry']['time_of_day'] = '夜'
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('时间跳变' in e for e in errors), errors)

    def test_project_check_rejects_missing_or_stale_frozen_board_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            internal = root / '内部'
            internal.mkdir()
            board = internal / '04-片段规划与逐镜表.md'
            board.write_text(BOARD, encoding='utf-8')
            facts = facts_of([seg('E01-SH01', 'E01-SH02'), seg('E01-SH02', None)])
            facts_path = internal / cf.FACTS_NAME
            facts_path.write_text(json.dumps(facts), encoding='utf-8')
            errors, _ = cf.check_project(root, BOARD, 'storyboard')
            self.assertTrue(any('逐镜表版本已过期或未登记' in e for e in errors), errors)
            facts['upstream'] = {'file': board.name, 'sha256': cf.wc.sha256_file(board)}
            facts_path.write_text(json.dumps(facts), encoding='utf-8')
            self.assertEqual(cf.check_project(root, BOARD, 'storyboard'), ([], []))
            board.write_text(BOARD + '\n新增冻结分镜说明\n', encoding='utf-8')
            errors, _ = cf.check_project(root, board.read_text(encoding='utf-8'), 'storyboard')
            self.assertTrue(any('逐镜表版本已过期或未登记' in e for e in errors), errors)

    def test_source_without_any_segments_fails_closed(self):
        errors, _ = cf.check_facts(facts_of([seg('E01-SH01', None)]), '# 无片段源文')
        self.assertTrue(any('没有可识别片段' in e for e in errors), errors)

    def test_old_schema_fails_in_memory_check(self):
        facts = facts_of([seg('E01-SH01', None)])
        facts['schema'] = 'continuity-facts/1'
        errors, _ = cf.check_facts(facts, BODY)
        self.assertTrue(any('schema' in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
