import copy
import unittest
from scripts import six_player_counterfactual_m4 as c

class ConditionalPanelTests(unittest.TestCase):
    def row(self):
        return dict(identities=[1,2,3,0,4,5], block=8, permutation=0,button=0,
                    actors=[3,4,5,0,1,2,3], actions=[['call',0]]*6+[['check',0]],
                    states=[dict(street='preflop',holes=[[0,1],[2,3],[4,5],[8,28],[9,10],[11,12]],board=[])]*7,
                    lookups=[dict(key='a'*32)]*7, rewards=[9]*6,deck=list(range(52)))
    def test_privileged_changes_cannot_affect_selection_or_output(self):
        row=self.row()
        before=list(c.candidates(0,row))
        row['rewards']=[-1000]*6;row['deck'].reverse()
        for state in row['states']:
            for seat in [0,1,2,4,5]:state['holes'][seat]=[50,51]
        self.assertEqual(before,list(c.candidates(0,row)))
        legal=before[0][2]
        self.assertEqual(set(legal),c.FIELDS)
        self.assertEqual(legal['hole'],[8,28])
        self.assertEqual(len(before),1) # First decision only per street.
    def test_first_decision_category_uses_known_cards_and_sampled_action(self):
        row=self.row();row['states'][0]['holes'][3]=[0,12];row['actions'][0]=['raise',200]
        self.assertTrue(list(c.candidates(0,row))[0][2]['stratum'].endswith('weak-raise'))
        row['states'][0]['holes'][3]=[44,33];row['actions'][0]=['fold',0]
        self.assertTrue(list(c.candidates(0,row))[0][2]['stratum'].endswith('good-fold'))
    def test_priority_and_disjoint_whole_blocks_and_empty_strata(self):
        candidates=[]
        for block in range(3):
            row=self.row();row['block']=block
            candidates.extend(c.candidates(0,row))
        roots,counts=c.select(candidates)
        self.assertEqual(len(roots),1)
        self.assertEqual(len(counts),36)
        self.assertEqual(c.select(list(reversed(candidates))),(roots,counts))
    def test_nonempty_stratum_excluded_by_whole_block_is_reported(self):
        _, block, root = list(c.candidates(0, self.row()))[0]
        first = copy.deepcopy(root);first['stratum'] = 'seat3/flop'
        chosen, counts = c.select([('0', block, first), ('1', block, root)])
        coverage = c.panel_coverage(chosen, counts)
        self.assertEqual(len(chosen), 1)
        self.assertGreater(counts[root['stratum']], 0)
        self.assertIn(root['stratum'], coverage['missing_strata'])
        self.assertEqual(coverage['missing_reasons'][root['stratum']], 'whole-block-exclusion')
        self.assertEqual(coverage['missing_reasons']['seat0/flop'], 'no-candidates')

    def test_quote_is_counts_and_cost_only(self):
        r=dict(status='passed',calibration_only=True,float64_and_work_reproduced=True,
               roots=1,load_and_k50_seconds=20,costs=[dict(worlds_per_pass=8,seconds_including_repeat=8)])
        q=c.quote(r)
        self.assertEqual(q['continuation_seconds'],2112)
        self.assertEqual(q['central_seconds'],2252)
        self.assertFalse(q['main_started'])
        r['calibration_only']=False
        with self.assertRaises(ValueError):c.quote(r)

if __name__=='__main__': unittest.main()
