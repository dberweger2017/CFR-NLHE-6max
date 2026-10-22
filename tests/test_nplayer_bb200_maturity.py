import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_bb200_maturity as study
from scripts.summarize_nplayer_bb200_feasibility import reserve_seconds

REPORT=Path(__file__).resolve().parents[1]/'docs/reports/nplayer-bb200-feasibility'


class MaturityTests(unittest.TestCase):
    def parent(self):
        return json.loads((REPORT/'results.json').read_text())['rows'][-1]

    def test_reserve_includes_the_metadata_allowance(self):
        quote=json.loads((REPORT/'next-allocation.json').read_text())
        self.assertAlmostEqual(reserve_seconds(quote['components_seconds']),4179.263974015036)
        self.assertAlmostEqual(quote['reserve_correction']['added_seconds'],240)
        self.assertAlmostEqual(reserve_seconds(quote['components_seconds'])-quote['reserve_correction']['previous_reserved_seconds'],240)

    def test_exact_parent_required_not_another_completed_model(self):
        study.validate_parent(self.parent())
        for field,value in [('sha256','0'*64),('frozen_at',10),('entries',250000000)]:
            parent=self.parent();parent[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate_parent(parent)
        parent=self.parent();parent['identity']['stacks']=[10000]*3
        with self.assertRaises(ValueError):study.validate_parent(parent)

    def test_only_added_nodes_count_as_continuation_throughput(self):
        parent=self.parent();row=copy.deepcopy(parent)
        row['counts']['nodes']=1000000017;row['entries']=250000000;row['frozen_at']=31000
        row['iteration']=40028
        row['active_training_seconds']=100
        result=study.continuation_metrics(row,parent)
        self.assertAlmostEqual(result['active_nodes_per_second'],(1000000017-study.PARENT_NODES)/100)
        self.assertTrue(result['growth_after_freeze_is_censored'])
        self.assertEqual(result['retained_capacity_fraction'],1)

    def test_native_iteration_boundary_overshoot_is_valid_but_not_unfrozen_or_under_cap(self):
        parent=self.parent();row=copy.deepcopy(parent)
        row.update(entries=250002537,frozen_at=38253,iteration=40028,active_training_seconds=114.802658556)
        row['counts']['nodes']=1000008098
        result=study.continuation_metrics(row,parent)
        self.assertEqual(result['iteration_boundary_entry_overshoot'],2537)
        self.assertGreater(result['retained_capacity_fraction'],1)
        row['frozen_at']=None
        with self.assertRaises(ValueError):study.continuation_metrics(row,parent)
        row['frozen_at']=38253;row['entries']=249999999
        with self.assertRaises(ValueError):study.continuation_metrics(row,parent)

    def test_completion_never_overwrites_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'completion output already exists'):
                study.finish_saved_endpoint(Path(directory),Path('/unused'),5400)

    def test_incomplete_nonfinite_or_lost_membership_cannot_pass(self):
        parent=self.parent();row=copy.deepcopy(parent);row['active_training_seconds']=10
        with self.assertRaises(ValueError):study.continuation_metrics(row,parent)
        row['counts']['nodes']=1000000001
        for value in (0,float('nan'),float('inf')):
            row['active_training_seconds']=value
            with self.subTest(value=value),self.assertRaises(ValueError):study.continuation_metrics(row,parent)
        row['active_training_seconds']=10;row['entries']=parent['entries']-1
        with self.assertRaises(ValueError):study.continuation_metrics(row,parent)

    def test_completed_attempt_never_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'config.json').write_text('{}');(root/'status.json').write_text('{}')
            with patch.object(study,'validate_config'):
                with self.assertRaisesRegex(ValueError,'attempt already exists'):study.run(root,5400)


if __name__=='__main__':unittest.main()
