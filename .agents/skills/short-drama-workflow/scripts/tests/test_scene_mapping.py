import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('validator_scene', Path(__file__).resolve().parents[1] / 'validate_compact_package.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class SceneMappingTests(unittest.TestCase):
    def check(self, rows, scenes=None):
        errors = []
        v.check_scene_mapping('【时间轴】\n'+rows+'\n【收尾】结束', scenes or ['LOC_06', 'LOC_05'], 'E03/SH09', errors)
        return errors

    def test_two_scenes_with_explicit_cut_pass(self):
        self.assertEqual(self.check('0-23.5秒，镜头：近景，场景锚：LOC_06。\n23.5-30秒，硬切，镜头：中景，场景锚：LOC_05。'), [])

    def test_missing_anchor_fails(self):
        self.assertTrue(self.check('0-30秒，镜头：近景。'))

    def test_unbound_scene_fails(self):
        self.assertTrue(self.check('0-30秒，场景锚：LOC_99。'))

    def test_uncut_transition_fails(self):
        self.assertTrue(self.check('0-23.5秒，场景锚：LOC_06。\n23.5-30秒，场景锚：LOC_05。'))

    def test_double_anchor_in_one_shot_fails(self):
        self.assertTrue(self.check('0-30秒，场景锚：LOC_06，场景锚：LOC_05。'))

    def test_unused_scene_fails(self):
        self.assertTrue(self.check('0-30秒，场景锚：LOC_06。'))


if __name__ == '__main__':
    unittest.main()
