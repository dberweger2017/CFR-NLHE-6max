import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.river_whole_hand_pilot import pair_proof, stats, LINEUPS, ROOTS


class PairingTests(unittest.TestCase):
    def pair(self, mutate=None):
        with tempfile.TemporaryDirectory() as tmp:
            header={'identity':'fixture','blocks':1,'hands':1,'seed':1,'policies':['a','b','c']}
            state={'street':'river','public':'same'}
            row={'hand':0,'block':0,'permutation':0,'identities':[0,1,2],
                 'deck':[0,1,2],'button':0,'states':[state,{'done':True}],
                 'actors':[0],'actions':[['check',0]],'rewards':[0,0,0],
                 'search_ledgers':[{'search':{'installed':True}}]}
            other=copy.deepcopy(row)
            if mutate:mutate(other)
            paths=[Path(tmp)/'off',Path(tmp)/'on']
            for p,r in zip(paths,[row,other]):p.write_text(json.dumps(header)+'\n'+json.dumps(r)+'\n')
            return pair_proof(*paths)

    def test_same_path_and_eligible_changed_river_action(self):
        self.assertEqual(self.pair()['hands_with_changed_action_path'],0)
        self.assertEqual(self.pair(lambda r:r['actions'].__setitem__(0,['raise',100]))['hands_with_changed_action_path'],1)

    def test_changed_deal_or_pre_river_or_script_action_rejected(self):
        for field,value in [('deck',[3,4,5]),('identities',[1,0,2])]:
            with self.assertRaises(ValueError):self.pair(lambda r:r.__setitem__(field,value))
        def bad(r):
            r['actions'][0]=['raise',100]
            r['states'][0]['street']='turn'
        with self.assertRaises(ValueError):self.pair(bad)
        def not_installed(r):
            r['actions'][0]=['raise',100]
            r['search_ledgers'][0]['search']['installed']=False
        with self.assertRaises(ValueError):self.pair(not_installed)

    def test_same_path_different_settlement_is_rejected(self):
        with self.assertRaises(ValueError):self.pair(lambda r:r['rewards'].__setitem__(0,1))

    def test_fixed_design_and_tail_statistics(self):
        self.assertEqual(len(LINEUPS),6)
        self.assertEqual(6*128*6*2,9216)
        self.assertEqual(len(set(ROOTS.values())),3)
        self.assertEqual(stats([1,2,3,100])['max'],100)
        self.assertEqual(stats([]),{'n':0})


if __name__=='__main__':unittest.main()
