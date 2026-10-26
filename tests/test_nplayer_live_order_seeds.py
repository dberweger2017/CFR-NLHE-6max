import json
import tempfile
import unittest
from pathlib import Path

from scripts import nplayer_live_order_seeds as seeds
from scripts import nplayer_pressure_screen as screen


def summary(primary_lower, harm=()):
    fields = {}
    for field in screen.FIELDS:
        lower = primary_lower if field == seeds.PRIMARY else -1.0
        fields[field] = {'change': {'adjusted': {'mean_bb100': lower + 5, 'lower95_bb100': lower, 'upper95_bb100': lower + 10}},
                         'harm_flag': field in harm}
    return {'fields': fields}


class CombineTests(unittest.TestCase):
    def run_combine(self, specs):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name, s in specs.items():
                p = Path(tmp) / f'{name}.json'
                p.write_text(json.dumps(s))
                paths.append(f'{name}={p}')
            out = Path(tmp) / 'results'
            seeds.combine(type('A', (), {'summary': paths, 'reference': 'ref', 'results': out}))
            self.assertTrue((out / 'seeds.csv').exists())
            return json.loads((out / 'seeds.json').read_text())

    def test_both_new_seeds_must_clear_zero(self):
        self.assertEqual(self.run_combine({'ref': summary(-3), 'a': summary(2), 'b': summary(1)})['verdict'], 'confirmed')
        self.assertEqual(self.run_combine({'ref': summary(9), 'a': summary(2), 'b': summary(-1)})['verdict'], 'not confirmed')

    def test_across_seed_interval_and_harm_flags(self):
        result = self.run_combine({'ref': summary(0, harm=('check-call',)), 'a': summary(10), 'b': summary(20)})
        across = result['fields'][seeds.PRIMARY]['across_seeds']
        self.assertAlmostEqual(across['mean_bb100'], 15.0)
        self.assertAlmostEqual(across['sd_bb100'], 10.0)
        # t(0.975, 2) = 4.303: half-width 4.303 * 10 / sqrt(3).
        self.assertAlmostEqual(across['upper95_bb100'] - across['mean_bb100'], 4.3027 * 10 / 3 ** 0.5, places=2)
        self.assertEqual(result['fields']['check-call']['harm_flags'], ['ref'])


if __name__ == '__main__':
    unittest.main()
