import json
import tempfile
import unittest
from pathlib import Path

from scripts import nplayer_live_order_variants as variants
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen
from tests import test_nplayer_loss_diagnosis as fixtures


def summary(mean, se):
    fields = {}
    for field in screen.FIELDS:
        fields[field] = {'change': {'adjusted': {'mean_bb100': mean, 'standard_error_bb100': se,
                                                 'lower95_bb100': mean - 1.96 * se, 'upper95_bb100': mean + 1.96 * se}},
                         'family_interval': [mean - 2.7 * se, mean + 2.7 * se],
                         'absolute': {'control': {'adjusted': {'mean_bb100': 0.0}}, 'variant': {'adjusted': {'mean_bb100': mean}}},
                         'harm_flag': mean + 2.7 * se < 0}
    return {'fields': fields}


def setUpModule():
    fixtures.setUpModule()


class CombineTests(unittest.TestCase):
    def test_primary_uses_bonferroni_over_the_two_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 2.1 standard errors clears an individual 95% bound but not a 97.5% one.
            paths = []
            for name, s in (('seat', summary(2.1, 1.0)), ('street', summary(3.0, 1.0))):
                p = Path(tmp) / f'{name}.json'
                p.write_text(json.dumps(s))
                paths.append(f'{name}={p}')
            variants.combine(type('A', (), {'summary': paths, 'results': Path(tmp) / 'r'}))
            result = json.loads((Path(tmp) / 'r' / 'variants.json').read_text())
            self.assertEqual(result['variants']['seat']['verdict'], 'not shown')
            self.assertEqual(result['variants']['street']['verdict'], 'improved')
            self.assertEqual(result['variants']['street']['fields']['random']['decision_interval_type'], 'Bonferroni 95% over seven fields')


@unittest.skipUnless(fixtures.ARENA.exists() and fixtures.EQUITY.exists(), 'build nplayer_paired_arena and nplayer_allin_equity first')
class HeadToHeadReportTests(unittest.TestCase):
    def test_identical_arms_give_zero_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for bank in range(screen.BANKS):
                for field in variants.H2H_FIELDS:
                    for arm in ('control', 'later'):
                        diagnosis.scan_file((str(fixtures.FIXTURE), tmp, f'{arm}-b{bank}', field, None, None, None))
            diagnosis.equity(type('A', (), {'out': out, 'binary': fixtures.EQUITY}))
            variants.h2h_report(type('A', (), {'out': out, 'results': out / 'results'}))
            result = json.loads((out / 'results' / 'h2h.json').read_text())
            for field in variants.H2H_FIELDS:
                self.assertEqual(result['fields'][field]['change_50b_minus_10b']['mean_bb100'], 0.0)


if __name__ == '__main__':
    unittest.main()
