from copy import deepcopy
import unittest
from scripts import nplayer_trace_divergence as diagnosis


def hand(actions,status='positive_mass',reward=0,street='preflop'):
    states=[dict(actor=0,street=street,pot=150,legal=dict(check=False,call=100,raise_to=[200,10000]),holes=[[0,1],[2,3],[4,5],[6,7],[8,9]]) for _ in actions]+[dict(finished=True)]
    return dict(hand=0,block=0,permutation=0,identities=list(range(5)),deck=list(range(52)),button=0,stacks=[10000]*5,sb=50,bb=100,
        actors=[0]*len(actions),actions=actions,states=states,lookups=[dict(status=status,key='0'*32) for _ in actions],rewards=[reward,-reward,0,0,0],settlement=dict(rewards=[reward,-reward,0,0,0]))


class DivergenceTests(unittest.TestCase):
    def test_identical_and_changed_action_all_streets(self):
        for street in ('preflop','flop','turn','river'):
            a=hand([['call',0]],street=street);self.assertIsNone(diagnosis.first_divergence(a,deepcopy(a)))
            b=hand([['raise',300]],reward=500,street=street);z=diagnosis.first_divergence(a,b)
            self.assertEqual((z['index'],z['street'],z['left_action'],z['right_raise_to']),(0,street,'call',300))
            self.assertNotIn('holes',z)
    def test_first_difference_only_and_category_reconciliation(self):
        a=hand([['call',0],['check',0]]);b=hand([['call',0],['raise',400]],reward=100,street='preflop')
        acc=diagnosis.Accounting();z=acc.add(a,b);self.assertEqual(z['index'],1)
        acc.add(a,deepcopy(a));r=acc.result();self.assertEqual(r['paired_mean_bb100'],50)
        self.assertEqual((r['first_divergences'],r['no_divergence_hands']),(1,1))
        for group in r['first_divergence_groups'].values():self.assertEqual(sum(x['contribution_bb100'] for x in group.values()),50)
    def test_wrong_deal_public_state_and_opponent_mismatch_reject(self):
        a=hand([['call',0]])
        for key,value in [('deck',[1]*52),('identities',[1,0,2,3,4]),('button',1)]:
            b=deepcopy(a);b[key]=value
            with self.assertRaisesRegex(ValueError,'paired deal'):diagnosis.first_divergence(a,b)
        b=hand([['raise',300]]);b['states'][0]['pot']=160
        with self.assertRaisesRegex(ValueError,'state/actor'):diagnosis.first_divergence(a,b)
        a['actors']=[1];b=deepcopy(a);b['actions']=[['raise',300]]
        with self.assertRaisesRegex(ValueError,'fixed opponent'):diagnosis.first_divergence(a,b)
    def test_missing_missing_and_changed_key_refuse(self):
        a=hand([['call',0]],status='missing');b=hand([['raise',300]],status='missing')
        with self.assertRaisesRegex(ValueError,'uniform missing'):diagnosis.first_divergence(a,b)
        b['lookups'][0]['key']='1'*32
        with self.assertRaisesRegex(ValueError,'different key'):diagnosis.first_divergence(a,b)
    def test_mass_labels_preserved_and_private_cards_ignored(self):
        a=hand([['call',0]],status='zero_mass');b=hand([['raise',300]],status='positive_mass');b['states'][0]['holes']=[[51,50]]*5
        z=diagnosis.first_divergence(a,b);self.assertEqual((z['left_status'],z['right_status']),('zero_mass','positive_mass'))
        self.assertNotIn('holes',diagnosis.public(a['states'][0]))
    def test_unequal_length_or_payoff_without_divergence_refuse(self):
        a=hand([['call',0]])
        with self.assertRaisesRegex(ValueError,'unequal trajectory'):diagnosis.first_divergence(a,hand([['call',0],['check',0]]))
        with self.assertRaisesRegex(ValueError,'different payoff'):diagnosis.first_divergence(a,hand([['call',0]],reward=1))
