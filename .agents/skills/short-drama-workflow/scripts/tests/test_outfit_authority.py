"""Per-wearer clothing authority, independent of legacy package fixtures."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('validator', Path(__file__).resolve().parents[1] / 'validate_compact_package.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


def check(role='身份基准（脸、发型、体态）', public=None, second=False, scope=None, timeline='0-5秒，娜琳站在窗边。', extra=''):
    garment = '真实服装产品摄影，单张平铺服装图。套装清单：米色棉裙。\n本套装供 CHAR_01 穿着。'
    if scope:
        garment += '\n覆盖范围：' + scope
    assets = [dict(code='CHAR_01', kind='角色', name='娜琳', prompt='固定服装：白色衬衫。'),
              dict(code='PROP_08', kind='道具', name='娜琳·棉裙', prompt=garment)]
    reference = f'CHAR_01＝{role}；PROP_08＝本段着装唯一基准，由 CHAR_01 穿着。'
    bindings = {'角色': ['CHAR_01'], '道具': ['PROP_08']}
    if public is None:
        public = '【角色一致性】娜琳：身份外观遵循 CHAR_01 人物参考图。\n着装来源：CHAR_01＝PROP_08（替换默认着装）。'
    if second:
        assets.append(dict(code='PROP_09', kind='道具', name='娜琳·外衣', prompt='真实服装产品摄影，单张平铺服装图。\n本套装供 CHAR_01 穿着。' + ('\n覆盖范围：上装' if scope else '')))
        bindings['道具'].append('PROP_09')
        reference += '\nPROP_09＝本段着装唯一基准，由 CHAR_01 穿着。'
        public += '\n着装来源：CHAR_01＝PROP_09（覆盖范围：上装）。'
    prompt = f'【参考】{reference}\n【公共总规范】{public}{extra}\n【时间轴】{timeline}\n【收尾】停在窗边。'
    data = {'assets': assets, 'episodes': [dict(code='E01', shots=[dict(code='SH01', bindings=bindings, prompts={'视频提示词': prompt})])]}
    errors, warnings = [], []
    v.check_outfit_consistency(data, {'CHAR_01': '娜琳'}, errors, warnings)
    return [e for e in errors if 'OUTFIT-04' in e]


class OutfitAuthorityTests(unittest.TestCase):
    def test_split_authority_passes(self):
        self.assertEqual(check(), [])

    def test_screenshot_double_authority_fails(self):
        self.assertTrue(check(role='身份与服装唯一基准（单人塑像图，全片不变）'))

    def test_default_clothing_reference_conflicts_with_variant(self):
        self.assertTrue(check(role='身份与默认着装基准', public=''))

    def test_identity_forever_is_not_clothing_lock(self):
        self.assertEqual(check(role='身份基准，全片不变'), [])

    def test_missing_role_reference_fails(self):
        self.assertTrue(check(role='参考图'))

    def test_reference_only_authority_passes(self):
        self.assertEqual(check(public=''), [])

    def test_partial_reference_only_authority_passes(self):
        self.assertEqual(check(public='', scope='下装'), [])

    def test_prop_owner_is_not_a_role_reference_declaration(self):
        entries = v.reference_entries('PROP_08＝服装唯一基准，由 CHAR_01 穿着。')
        self.assertNotIn('CHAR_01', entries)

    def test_wrong_clothing_pointer_fails(self):
        self.assertTrue(check(public='着装来源：CHAR_01＝PROP_09。'))

    def test_generic_clothing_lock_fails(self):
        self.assertTrue(check(extra='\n每张角色资产图仅参考面容、体型、服装和配饰。'))

    def test_two_unscoped_outfits_fail(self):
        self.assertTrue(check(second=True))

    def test_disjoint_partial_outfits_pass(self):
        self.assertEqual(check(second=True, scope='下装'), [])

    def test_overlapping_outfits_fail(self):
        self.assertTrue(check(second=True, scope='上装'))

    def test_timed_owner_change_passes(self):
        self.assertEqual(check(second=True, timeline='0-5秒，娜琳脱下外套，换上另一套衣服。'), [])

    def test_other_character_change_does_not_exempt(self):
        self.assertTrue(check(second=True, timeline='0-5秒，苏帕脱下外套；娜琳看向窗外。'))


if __name__ == '__main__':
    unittest.main()
