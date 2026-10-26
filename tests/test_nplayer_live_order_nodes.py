import json
import tempfile
import unittest
from pathlib import Path

from scripts import nplayer_live_order_nodes as nodes
from scripts import nplayer_pressure_screen as screen


def summary(primary):
    lower, upper = primary
    fields = {}
    for field in screen.FIELDS:
        lo, hi = (lower, upper) if field == nodes.PRIMARY else (-5.0, 5.0)
        fields[field] = {'change': {'adjusted': {'mean_bb100': (lo + hi) / 2, 'lower95_bb100': lo, 'upper95_bb100': hi}},
                         'absolute': {'control': {'adjusted': {'mean_bb100': 1.0}}, 'later': {'adjusted': {'mean_bb100': 2.0}}},
                         'harm_flag': field == 'check-call'}
    return {'fields': fields}


class LadderTests(unittest.TestCase):
    def run_ladder(self, first, second):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name, s in (('10b-30b', summary(first)), ('30b-50b', summary(second))):
                p = Path(tmp) / f'{name}.json'
                p.write_text(json.dumps(s))
                paths.append(f'{name}={p}')
            out = Path(tmp) / 'results'
            nodes.ladder(type('A', (), {'summary': paths, 'results': out}))
            self.assertTrue((out / 'ladder.csv').exists())
            return json.loads((out / 'ladder.json').read_text())

    def test_primary_is_the_first_contrast_and_the_second_is_classified(self):
        result = self.run_ladder((3, 20), (-4, 6))
        self.assertEqual((result['verdict'], result['second_contrast']), ('improved', 'not resolved'))
        result = self.run_ladder((-1, 20), (2, 9))
        self.assertEqual((result['verdict'], result['second_contrast']), ('not shown', 'improved'))
        self.assertEqual(self.run_ladder((1, 2), (-9, -1))['second_contrast'], 'worse')
        self.assertTrue(result['fields']['check-call']['10b-30b']['harm_flag'])


if __name__ == '__main__':
    unittest.main()
