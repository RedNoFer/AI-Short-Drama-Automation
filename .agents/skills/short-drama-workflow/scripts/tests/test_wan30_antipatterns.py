#!/usr/bin/env python3
"""audit_wan30_antipatterns.py 的回归自测：正反样本必须同时成立。

运行：python3 scripts/tests/test_wan30_antipatterns.py
新增/修改 WAN30-01 反例规则时先跑本测试。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "wan30_audit", ROOT / "scripts" / "audit_wan30_antipatterns.py"
)
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)
POLICY = ROOT / "policy.json"


def make_pkg(rows: str, public: str = "统一冷灰光影，真人实拍电影质感。") -> str:
    return f"""# 精简制作包

## 剧集 E01｜测试

### 片段 SH01｜30秒｜测试

#### 视频提示词

```text
【参考】CHAR_01=阿泽外观锁定；LOC_01=起点路段。
【公共总规范】{public}
【时间轴】
{rows}
【收尾】阿泽走远，下一片段承接。
```
"""


CLEAN_ROWS = "\n".join(
    [
        "0-10秒，镜头：中景，侧45°机位，手持轻晃。画面：阿泽伸手抓起绳头，转身把绳头甩上肩；苏晚抬手按住被风吹起的纸角。全员不看镜头，视线落在远处路牌。",
        "10-20秒，硬切。镜头：近景，右后方45°。画面：老杨蹲下，把绳头一圈圈收进掌心；小林退开半步，抬手擦掉额头的汗。全员不看镜头。",
        "20-30秒，硬切。镜头：全景，侧45°。画面：三个人错位站在车头两侧，阿泽弯腰抹轮眉，苏晚翻笔记本，老杨收绳，另两人留在画外只给肩线。全员不看镜头。",
    ]
)


class Wan30AntiPatternTests(unittest.TestCase):
    def _audit(self, rows: str, public: str = "统一冷灰光影，真人实拍电影质感。") -> dict:
        pkg = make_pkg(rows, public)
        tmp = ROOT / "scripts" / "tests" / "_tmp_wan30_audit.md"
        tmp.write_text(pkg, encoding="utf-8")
        try:
            return audit_mod.audit(tmp, POLICY)
        finally:
            tmp.unlink(missing_ok=True)

    def test_clean_rows_pass(self):
        result = self._audit(CLEAN_ROWS)
        self.assertEqual(result["errors"], 0, result["issues"])
        self.assertEqual(result["warnings"], 0, result["issues"])
        self.assertEqual(result["camera_missing_prefix"], 0)
        self.assertEqual(result["no_gaze_segments"], 0)

    def test_public_section_share_does_not_trigger_length_quota(self):
        """公共层比例不能作为阻断依据；重复的语义质量仍由评审判断。"""
        result = self._audit(CLEAN_ROWS, public="统一冷灰自然光。" * 200)
        self.assertEqual(result["errors"], 0, result["issues"])
        self.assertEqual(result["warnings"], 0, result["issues"])

    def test_reaction_shot_does_not_require_extra_action_words(self):
        result = self._audit(
            "0-3秒，镜头：近景，阿泽侧前方平视，向前短推。阿泽眼神骤然失去焦点，唇线绷紧。全员不看镜头。")
        self.assertEqual(result["errors"], 0, result["issues"])
        self.assertEqual(result["warnings"], 0, result["issues"])

    def test_blocking_term_is_error(self):
        result = self._audit(CLEAN_ROWS.replace("三个人错位站在车头两侧", "五人并肩站在车头前", 1))
        self.assertGreater(result["errors"], 0)
        self.assertTrue(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_two_person_side_by_side_not_blocking(self):
        result = self._audit(
            "0-10秒，镜头：中景。画面：阿泽与老杨并肩走在车前，两人抬手扶住车门。全员不看镜头。"
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_dialogue_metaphor_not_blocking(self):
        result = self._audit(
            '0-10秒，镜头：中景。画面：阿泽抬手按住车顶，说："我们五人同心并肩。"全员不看镜头。'
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_shadow_lineup_not_blocking(self):
        result = self._audit(
            "0-10秒，镜头：全景。画面：晨光把五个人的影子排成一排，阿泽抬手关上车门。全员不看镜头。"
        )
        self.assertFalse(any(i["kind"] == "forbidden_blocking" for i in result["issues"]))

    def test_camera_must_be_front(self):
        long_desc = "晨雾漫过路面，" * 20
        result = self._audit(
            "0-10秒，" + long_desc + "阿泽站着，镜头：中景，侧45°。画面：他抬手。\n"
            "10-30秒，硬切。镜头：全景。画面：他转身走。全员不看镜头。"
        )
        self.assertGreater(result["camera_missing_prefix"], 0)
        self.assertTrue(any(i["kind"] == "camera_late" for i in result["issues"]))

    def test_still_life_too_long(self):
        result = self._audit(
            "0-5秒，包裹静置引擎盖，纸角被风掀起又落下。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起包裹，转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "still_life_too_long" for i in result["issues"]))

    def test_empty_shot_too_long(self):
        result = self._audit(
            "0-5秒，晨雾漫过路面，远处路牌在雾里若隐若现。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "empty_shot_too_long" for i in result["issues"]))

    def test_dialogue_shot_too_long(self):
        result = self._audit(
            '0-8秒，镜头：中景。画面：阿泽抬头，说："你好。"\n'
            "8-30秒，硬切。镜头：全景。画面：他转身走。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "dialogue_shot_too_long" for i in result["issues"]))

    def test_declared_dialogue_window_uses_speech_duration(self):
        result = self._audit(
            '0-8秒，镜头：中景。画面：阿泽边走边说“你好”，动作2.6秒、对白5.4秒。全员不看镜头。'
        )
        self.assertFalse(
            any(i["kind"] == "dialogue_shot_too_long" for i in result["issues"]),
            result["issues"],
        )

    def test_warm_light_word(self):
        result = self._audit(CLEAN_ROWS, public="清晨低角度金色逆光，真人实拍。")
        self.assertTrue(any(i["kind"] == "warm_light" for i in result["issues"]))

    def _risk_record(self, result: dict) -> dict:
        return {'schema_version': 1, 'dispositions': [
            {'issue_id': i['issue_id'], 'fingerprint': i['fingerprint'],
             'status': 'not_applicable', 'reason': '本场暖光来自已冻结的舞台灯',
             'evidence': '阶段2场景LOC_01光源表：舞台既有暖灯', 'reviewer': '独立评审员'}
            for i in result['issues'] if i['level'] == 'warning']}

    def test_warning_is_pending_without_review_record(self):
        result = self._audit(CLEAN_ROWS, public='既有舞台灯产生暖金光。全员不看镜头。')
        self.assertEqual(result['errors'], 0)
        self.assertGreater(result['unresolved_warnings'], 0)
        self.assertEqual(result['accepted_warnings'], 0)
        self.assertTrue(all(i.get('issue_id') and i.get('fingerprint') for i in result['issues']))

    def test_strict_requires_current_individual_disposition(self):
        with tempfile.TemporaryDirectory() as d:
            package = Path(d) / 'package.md'
            record = Path(d) / 'review.json'
            package.write_text(make_pkg(CLEAN_ROWS, '舞台既有暖金灯光。全员不看镜头。'), encoding='utf-8')
            result = audit_mod.audit(package, POLICY)
            command = [sys.executable, str(ROOT / 'scripts/audit_wan30_antipatterns.py'),
                       str(package), '--strict', '--json']
            pending = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(pending.returncode, 1, pending.stdout + pending.stderr)
            record.write_text(json.dumps(self._risk_record(result), ensure_ascii=False), encoding='utf-8')
            reviewed = subprocess.run(command + ['--review-record', str(record)], capture_output=True, text=True)
            self.assertEqual(reviewed.returncode, 0, reviewed.stdout + reviewed.stderr)
            review_result = json.loads(reviewed.stdout)
            self.assertEqual(review_result['unresolved_warnings'], 0)
            self.assertGreater(review_result['warnings'], 0)  # Original hit stays visible.
            self.assertIn('evidence', review_result['issues'][0]['disposition'])

    def test_disposition_stale_only_when_own_segment_or_rules_change(self):
        with tempfile.TemporaryDirectory() as d:
            package, record = Path(d) / 'package.md', Path(d) / 'review.json'
            original = make_pkg(CLEAN_ROWS, '舞台既有暖金灯光。全员不看镜头。')
            package.write_text(original, encoding='utf-8')
            record.write_text(json.dumps(self._risk_record(audit_mod.audit(package, POLICY))), encoding='utf-8')
            second = make_pkg(CLEAN_ROWS).replace('SH01', 'SH02')
            package.write_text(original + second, encoding='utf-8')
            unchanged = audit_mod.audit(package, POLICY, record)
            self.assertEqual(unchanged['errors'], 0, unchanged)
            self.assertEqual(unchanged['unresolved_warnings'], 0, unchanged)
            package.write_text(original.replace('阿泽走远', '阿泽慢慢走远'), encoding='utf-8')
            stale = audit_mod.audit(package, POLICY, record)
            self.assertGreater(stale['review_record_errors'], 0)
            self.assertGreater(stale['unresolved_warnings'], 0)

    def test_review_record_fields_and_duplicates_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            package, record = Path(d) / 'package.md', Path(d) / 'review.json'
            package.write_text(make_pkg(CLEAN_ROWS, '舞台既有暖金光。'), encoding='utf-8')
            valid = self._risk_record(audit_mod.audit(package, POLICY))
            for field in ('reason', 'evidence', 'reviewer', 'fingerprint', 'status', 'issue_id'):
                bad = json.loads(json.dumps(valid))
                bad['dispositions'][0][field] = ''
                record.write_text(json.dumps(bad), encoding='utf-8')
                result = audit_mod.audit(package, POLICY, record)
                self.assertGreater(result['errors'], 0, field)
            valid['dispositions'].append(dict(valid['dispositions'][0]))
            record.write_text(json.dumps(valid), encoding='utf-8')
            self.assertGreater(audit_mod.audit(package, POLICY, record)['errors'], 0)

    def test_hard_error_cannot_be_waived(self):
        with tempfile.TemporaryDirectory() as d:
            package, record = Path(d) / 'package.md', Path(d) / 'review.json'
            package.write_text(make_pkg(CLEAN_ROWS.replace('三个人错位站在车头两侧',
                                                        '五人并肩站在车头前')), encoding='utf-8')
            result = audit_mod.audit(package, POLICY)
            hard = next(i for i in result['issues'] if i['level'] == 'error')
            disposition = self._risk_record(result)
            disposition['dispositions'].append({
                'issue_id': hard['issue_id'], 'fingerprint': hard['fingerprint'],
                'status': 'resolved', 'reason': '不能用此记录解除硬错误',
                'evidence': '测试', 'reviewer': '测试评审'})
            record.write_text(json.dumps(disposition), encoding='utf-8')
            reviewed = audit_mod.audit(package, POLICY, record)
            self.assertGreater(reviewed['errors'], 0)
            self.assertGreater(reviewed['review_record_errors'], 0)

    def test_malformed_or_unknown_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            package, record = Path(d) / 'package.md', Path(d) / 'review.json'
            package.write_text(make_pkg(CLEAN_ROWS), encoding='utf-8')
            for raw in ('{broken', '{}', '{"schema_version":true,"dispositions":[]}'):
                record.write_text(raw, encoding='utf-8')
                self.assertGreater(audit_mod.audit(package, POLICY, record)['errors'], 0)
            self.assertGreater(audit_mod.audit(package, POLICY, Path(d) / 'missing.json')['errors'], 0)

    def test_negated_gold_filter_is_not_warm_light(self):
        result = self._audit(CLEAN_ROWS, public="低饱和自然光，不使用金色滤镜，真人实拍。")
        self.assertFalse(
            any(i["kind"] == "warm_light" for i in result["issues"]),
            result["issues"],
        )

    def test_gold_filter_excluded_by_lighting_clause_is_not_warm_light(self):
        result = self._audit(CLEAN_ROWS, public="不添加新灯位或金色滤镜，保持自然光。")
        self.assertFalse(
            any(i["kind"] == "warm_light" for i in result["issues"]),
            result["issues"],
        )

    def test_gold_jewelry_is_not_warm_light(self):
        result = self._audit(CLEAN_ROWS, public="金色耳饰仅在受光处保留一小片暖高光。")
        self.assertFalse(
            any(i["kind"] == "warm_light" for i in result["issues"]),
            result["issues"],
        )

    def test_legible_text_closeup(self):
        result = self._audit(
            "0-5秒，镜头：大特写。画面：字条上的墨色起笔清晰可读。\n"
            "5-30秒，硬切。镜头：中景。画面：阿泽伸手抓起字条，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "legible_text_closeup_risk" for i in result["issues"])
        )

    def test_missing_no_lens_gaze(self):
        result = self._audit(
            "0-30秒，镜头：中景。画面：阿泽伸手抓起绳头，转身走。"
        )
        self.assertTrue(any(i["kind"] == "missing_no_lens_gaze" for i in result["issues"]))

    def test_duplicate_timestamp_in_body(self):
        result = self._audit(
            "0-10秒，5秒，阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "duplicate_timestamp_in_body" for i in result["issues"])
        )

    def test_identity_overload(self):
        result = self._audit(
            "0-10秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠错位站在车头两侧，各自抬手整理装备。全员不看镜头。"
        )
        self.assertTrue(any(i["kind"] == "identity_overload" for i in result["issues"]))

    def test_five_person_shot_too_long(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：五人全景，阿泽、苏晚、老杨、许棠、小林错位站在车头两侧。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "five_person_shot_too_long" for i in result["issues"])
        )

    def test_five_person_face_overload(self):
        result = self._audit(
            "0-5秒，镜头：近景。画面：五人全景，阿泽、苏晚、老杨、许棠、小林站在车头前。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "five_person_face_overload" for i in result["issues"])
        )

    def test_group_dialogue_overload(self):
        result = self._audit(
            '0-8秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠围在车头，阿泽说："走。"全员不看镜头。'
        )
        self.assertTrue(
            any(i["kind"] == "group_dialogue_overload" for i in result["issues"])
        )

    def test_reflection_ambiguity(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：湖面倒影里站着阿泽，他抬手。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "reflection_ambiguity" for i in result["issues"])
        )

    def test_reflection_with_fantasy_tag_allowed(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：水下复刻倒影，幻境层，阿泽抬手。全员不看镜头。"
        )
        self.assertFalse(
            any(i["kind"] == "reflection_ambiguity" for i in result["issues"])
        )

    def test_group_shot_budget(self):
        result = self._audit(
            "0-5秒，镜头：全景。画面：阿泽、苏晚、老杨、许棠错位站在车头两侧。全员不看镜头。\n"
            "5-10秒，硬切。镜头：中景。画面：阿泽、苏晚、老杨、小林围在引擎盖旁。全员不看镜头。\n"
            "10-30秒，硬切。镜头：中景。画面：阿泽伸手抓起绳头，转身走。全员不看镜头。"
        )
        self.assertTrue(
            any(i["kind"] == "group_shot_budget" for i in result["issues"])
        )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
