import json
import tempfile
import unittest
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen
from tests import test_nplayer_loss_diagnosis as fixtures


def setUpModule():
    fixtures.setUpModule()


@unittest.skipUnless(fixtures.ARENA.exists() and fixtures.EQUITY.exists(), 'build nplayer_paired_arena and nplayer_allin_equity first')
class ReportTests(unittest.TestCase):
    def test_identical_arms_give_zero_change_no_verdict_and_no_harm(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for bank in range(screen.BANKS):
                for field in screen.FIELDS:
                    for arm in screen.ARMS:
                        diagnosis.scan_file((str(fixtures.FIXTURE), tmp, f'{arm}-b{bank}', field, None, None, None))
            diagnosis.equity(type('A', (), {'out': out, 'binary': fixtures.EQUITY}))
            screen.report(type('A', (), {'out': out, 'results': out / 'results'}))
            summary = json.loads((out / 'results/summary.json').read_text())
            self.assertEqual(summary['verdict'], 'not shown')
            self.assertEqual(summary['harm_flags'], [])
            primary = summary['fields'][screen.PRIMARY]
            self.assertEqual(primary['change']['adjusted']['mean_bb100'], 0.0)
            self.assertEqual(primary['untrained_share']['control'], primary['untrained_share']['pressure'])
            self.assertTrue((out / 'results/fields.csv').exists())


if __name__ == '__main__':
    unittest.main()
