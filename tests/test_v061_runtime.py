"""Real table configuration boundary, using lightweight decisions without models."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.play_api.service import PlayError
from src.play_api.table_service import SeatTable, TableService
from src.policies.v061_bundle import MODELS


class RuntimeBoundaryTest(unittest.TestCase):
    def test_exact_200bb_identity_restricted_sizing_and_wrong_table_refusal(self):
        metadata = next(iter(MODELS.values()))['metadata']
        identity = deepcopy(metadata['policy']['identity'])

        class Decisions:
            ready = dict(schema=identity['schema'], menu=identity['menu'], card_tables=identity['card_tables'])
            policies = {'qualified': dict(identity=identity, sha256=next(iter(MODELS.values()))['sha256'])}

        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp)/'private.sqlite'
            seats = ('human', 'policy:qualified', 'policy:qualified')
            table = SeatTable(seats, stack=20000)
            service = TableService(database, table, Decisions(), source_version='v0.6.1-prepared')
            try:
                self.assertEqual(service.identity['table']['stack'], 20000)
                self.assertEqual(service.identity['schema'], identity['schema'])
                with self.assertRaisesRegex(PlayError, 'restricted sizing'):
                    service.create('v061-free-sizing-refusal-0001', {'playMode': 'free'})
                view = service.create('v061-restricted-sizing-0001', {'playMode': 'restricted'})
                self.assertEqual(view['table']['table']['stack'], 20000)
            finally:
                service.close()
            for wrong in (SeatTable(seats), SeatTable(('human', 'policy:qualified'), stack=20000)):
                with self.assertRaisesRegex(ValueError, 'not loaded for this table'):
                    TableService(Path(temp)/'wrong.sqlite', wrong, Decisions())


if __name__ == '__main__':
    unittest.main()
