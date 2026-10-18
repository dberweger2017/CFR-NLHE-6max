import copy
import unittest
from scripts.run_nplayer_key_benchmark import SCHEMAS, same_counts, quote


def result(schema, seconds=20, save=20):
    return dict(events=[dict(event='trained', target=100_000_000, nodes=100_001_000,
        iteration=20000, entries=8_000_000, seconds=seconds, counts=dict(nodes=100_001_000)),
        dict(event='checkpoint',target=100_000_000,save_seconds=save)])


class BenchmarkTests(unittest.TestCase):
    def test_cost_quote_includes_traversal_io_audit_and_loading(self):
        pilots={s:result(s) for s in SCHEMAS}
        audit=dict(events=[dict(event='audit-trained',seconds=30)])
        q=quote(pilots,audit)
        self.assertGreater(q['projected_seconds'],3*20*30+30*32)
        for change in ['train','save','audit']:
            changed=copy.deepcopy(pilots);other=copy.deepcopy(audit)
            if change=='audit':other['events'][0]['seconds']*=2
            else:changed['v1']['events'][0 if change=='train' else 1]['seconds' if change=='train' else 'save_seconds']*=2
            self.assertGreater(quote(changed,other)['projected_seconds'],q['projected_seconds'])

    def test_cross_schema_must_match_all_targets_and_accounting(self):
        rows={s:result(s) for s in SCHEMAS};same_counts(rows)
        for field in ['nodes','iteration','entries','counts','target']:
            changed=copy.deepcopy(rows)
            changed[SCHEMAS[1]]['events'][0][field]={'nodes':1} if field=='counts' else 1
            with self.subTest(field=field),self.assertRaises(ValueError):same_counts(changed)


if __name__=='__main__':unittest.main()
