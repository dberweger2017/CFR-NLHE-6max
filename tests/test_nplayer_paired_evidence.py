from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_paired_evidence as evidence


class PairedEvidenceTests(unittest.TestCase):
    def test_cyclic_schedule_balances_seats_and_positions_without_factorial_growth(self):
        for n in (4,5,6):
            rows=evidence.seating(n);self.assertEqual(len(rows),n)
            for identity in range(n):
                for seat in range(n):self.assertEqual(sum(r[seat]==identity for r in rows),1)
                for button in range(n):self.assertEqual(sorted((r.index(identity)-button)%n for r in rows),list(range(n)))
        self.assertEqual(len(evidence.seating(6)),6)

    def test_schedule_rejects_duplicates_wrong_labels_unbalanced_and_boolean_ids(self):
        for n,rows in ((3,None),(4,[]),(4,[[0,1,2,3]]*4),(4,[[0,1,2,3],[0,1,3,2],[0,2,1,3],[0,2,3,1]]),(4,[[False,1,2,3]]*4)):
            with self.subTest(rows=rows),self.assertRaises(ValueError):evidence.seating(n,rows)

    def fixture(self,root,changed=False):
        n=4;schedule=evidence.seating(n)
        h=dict(format='nplayer-privileged-policy-replay-v1',harness='nplayer-paired-v1',identity=dict(players=n,stacks=[10000]*n,small_blind=50,big_blind=100),
            blocks=2,hands=8,seed=12,schedule=schedule,policies=[{'script':'check-call'}]*n,distinct_policy_instances=n)
        data=[]
        for block in range(2):
            for rotation,ids in enumerate(schedule):
                data.append(dict(hand=len(data),block=block,permutation=rotation,identities=ids,button=block%n,deck=list(range(52)),
                    stacks=[10000]*n,sb=50,bb=100,rewards=[0]*n,lookups=[{'status':'not_applicable'}],actions=[['check',0]],actors=[0],states=[{'street':'preflop'},{}]))
        def save(name,header,records):
            p=root/name;p.write_text('\n'.join(json.dumps(x) for x in [header,*records])+'\n');return p
        a=save('a',h,data);hb=deepcopy(h);db=deepcopy(data)
        if changed:
            hb['policies'][0]={'script':'random'}
            for row in db:
                focal=row['identities'].index(0);row['rewards'][focal]=100;row['rewards'][(focal+1)%n]=-100
        b=save('b',hb,db)
        pa=root/'pa';pb=root/'pb'
        for trace,proof in ((a,pa),(b,pb)):proof.write_text(json.dumps(dict(status='passed',trace_sha256=evidence.sha(trace),hands=8,players=n)))
        return a,b,a,b,pa,pb

    def test_identical_arms_have_exact_zero_per_block_and_overall(self):
        with tempfile.TemporaryDirectory() as d:
            result=evidence.verified_pair(*self.fixture(Path(d)))
            self.assertTrue(result['self_exact_zero']);self.assertEqual(result['block_values_bb100'],[0,0]);self.assertEqual(result['contrast']['lower95_bb100'],0)

    def test_changed_focal_comparison_is_not_halved_and_preserves_each_seat(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(evidence,'interval',side_effect=lambda v:{'mean_bb100':sum(v)/len(v)}):
                result=evidence.verified_pair(*self.fixture(Path(d),True))
            self.assertEqual(result['contrast']['mean_bb100'],100);self.assertEqual(result['block_values_bb100'],[100,100])
            self.assertTrue(all(s['mean_bb100']==100 for s in result['by_seat']));self.assertFalse(result['self_comparison'])

    def test_wrong_opponent_root_deck_and_schedule_are_refused(self):
        for mutation in ('opponent','root','deck','schedule'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                args=list(self.fixture(Path(d),True));b=args[1];values=[json.loads(line) for line in b.read_text().splitlines()]
                if mutation=='opponent':values[0]['policies'][1]={'script':'random'}
                elif mutation=='root':values[0]['seed']+=1
                elif mutation=='deck':values[1]['deck'][0:2]=reversed(values[1]['deck'][0:2])
                else:values[1]['identities']=[1,0,2,3]
                b.write_text('\n'.join(json.dumps(x) for x in values)+'\n');proof=json.loads(args[5].read_text());proof['trace_sha256']=evidence.sha(b);args[5].write_text(json.dumps(proof))
                with self.assertRaises(ValueError):evidence.verified_pair(*args)

    def test_incomplete_replay_or_reproduction_cannot_reach_readout(self):
        with tempfile.TemporaryDirectory() as d:
            args=list(self.fixture(Path(d)));args[4].write_text(json.dumps(dict(status='failed',trace_sha256=evidence.sha(args[0]))))
            with self.assertRaises(ValueError):evidence.verified_pair(*args)

    def test_lookup_coordinates_and_unknown_mass_labels_are_refused(self):
        h=dict(identity=dict(players=4,stacks=[10000]*4,small_blind=50,big_blind=100),policies=[{'sha256':'a'*64}]*4)
        row=dict(hand=0,block=0,permutation=0,identities=[0,1,2,3],button=0,stacks=[10000]*4,sb=50,bb=100,rewards=[0]*4,
            actions=[['check',0]],actors=[0],states=[{'street':'preflop'},{}],lookups=[dict(status='positive_mass',identity=0,seat=0,position=0,street=0,key='a'*32)])
        evidence.validate_row(row,0,h,4,evidence.seating(4))
        for key,value in [('status','unknown'),('seat',1),('identity',2),('position',1),('key','x'*32)]:
            bad=deepcopy(row);bad['lookups'][0][key]=value
            with self.assertRaises(ValueError):evidence.validate_row(bad,0,h,4,evidence.seating(4))


if __name__=='__main__':unittest.main()
