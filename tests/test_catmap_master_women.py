import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from libs.catmap import CatMap


class MasterWomenTests(unittest.TestCase):
    def allowed(self, tokens, age, gender='F'):
        with contextlib.redirect_stderr(io.StringIO()):
            mapping = CatMap('BCProvincialCX2026')
            return mapping.get_event_category(
                {'Cyclocross': tokens}, gender, age, discipline='Cyclocross'
            )

    def test_split_and_legacy_forms_equivalent(self):
        for band, age in [('35-44', 40), ('45-54', 50), ('55-64', 56), ('65+', 70)]:
            tokens = ['Master Women', band, 'Cat 2']
            actual, original = self.allowed(tokens, age)
            expected, _ = self.allowed(['Master ' + band, 'Cat 2'], age)
            self.assertEqual(actual, expected)
            self.assertIn('Master ' + band, actual)
            self.assertEqual(original['Cyclocross'], tokens)
            self.assertEqual(tokens, ['Master Women', band, 'Cat 2'])

    def test_age_bounds_still_apply(self):
        allowed, _ = self.allowed(['Master Women', '55-64', 'Cat 2'], 50)
        self.assertNotIn('Master 55-64', allowed)
        self.assertNotIn('Master 45-54', allowed)

    def test_no_age_band_does_not_qualify(self):
        allowed, _ = self.allowed(['Master Women', 'Cat 2'], 56)
        self.assertFalse(any(c.startswith('Master ') for c in allowed))

    def test_ability_alone_does_not_qualify(self):
        allowed, _ = self.allowed(['Cat 2'], 56)
        self.assertFalse(any(c.startswith('Master ') for c in allowed))


if __name__ == '__main__':
    unittest.main()
