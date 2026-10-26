from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts import nplayer_six_player_trajectory as study
from tests.test_nplayer_trace_divergence import hand


def fixture(actions,status='positive_mass',reward=0,street='preflop'):
    r=hand(actions,status,reward,street);r['identities']=list(range(6));r['stacks']=[10000]*6;r['rewards'].append(0);r['settlement']['rewards'].append(0)
    for s in r['states'][:-1]:s['holes'].append([10,11])
    return r


class TrajectoryTests(unittest.TestCase):
    def test_all_streets_support_partitions_and_unchanged_hands(self):
        for street in study.STREETS:
            a=fixture([['call',0]],'missing',street=street);b=fixture([['raise',300]],reward=600,street=street)
            acc=study.Accounting(['3b','10b'],2);acc.add(a,b);acc.add(a,deepcopy(a));r=acc.result(100)
            self.assertEqual((r['hands'],r['first_divergences'],r['unchanged_hands']),(2,1,1));self.assertEqual(r['mean_bb100'],300)
            for groups in r['groups'].values():
                self.assertEqual(sum(g['hands'] for g in groups.values()),2);self.assertEqual(sum(g['unconditional_contribution_bb100'] for g in groups.values()),300)
            self.assertEqual(r['groups']['lookup_pair']['missing->positive_mass']['hands'],1)
    def test_10b15b_labels_raise_size_and_later_missing(self):
        a=fixture([['raise',200],['call',0]],reward=500);b=fixture([['raise',400],['fold',0]],reward=-500)
        b['lookups'][1]['status']='missing';acc=study.Accounting(['10b','15b'],1);acc.add(a,b);r=acc.result(100)
        self.assertEqual(r['groups']['raise_size_direction']['higher']['hands'],1);self.assertEqual(r['groups']['action_pair']['raise->raise']['hands'],1)
        self.assertEqual(r['groups']['later_missing']['preflop/positive_mass->positive_mass/01']['hands'],1)
        self.assertTrue(any(k.startswith('15b/') for k in r['reached_focal_actions']));self.assertFalse(any(k.startswith('3b/') for k in r['reached_focal_actions']))
    def test_matched_prefix_not_extra_hand_contributions(self):
        a=fixture([['call',0],['check',0]]);b=fixture([['call',0],['raise',400]],reward=300)
        acc=study.Accounting(['3b','10b'],1);acc.add(a,b);r=acc.result(100)
        self.assertEqual(sum(r['matched_prefix_unchanged_actions'].values()),1)
        self.assertEqual(r['groups']['street']['preflop']['sum_delta_chips'],300)
    def test_uniform_fallback_cannot_be_first_change(self):
        for x in ['missing','zero_mass']:
            for y in ['missing','zero_mass']:
                a=fixture([['call',0]],x);b=fixture([['raise',300]],y)
                with self.subTest(x=x,y=y),self.assertRaises(ValueError):study.Accounting(['a','b'],1).add(a,b)
    def test_block_not_seating_is_uncertainty_unit(self):
        acc=study.Accounting(['3b','10b'],2)
        for reward in [0,200,400,600]:acc.add(fixture([['call',0]]),fixture([['raise',300]],reward=reward))
        r=acc.result(100);self.assertEqual(r['blocks'],2);self.assertEqual(r['mean_bb100'],300);self.assertEqual(r['standard_error_bb100'],200)
    def test_invalid_prefix_and_incomplete_block_fail(self):
        a=fixture([['call',0]]);b=deepcopy(a);b['states'][0]['legal']['call']=200
        with self.assertRaises(ValueError):study.Accounting(['a','b'],2).add(a,b)
        acc=study.Accounting(['a','b'],2);acc.add(a,deepcopy(a))
        with self.assertRaisesRegex(ValueError,'incomplete'):acc.result(100)
    def test_manifest_inventory_has_all24_files_and16_panels(self):
        m=json.loads((Path(__file__).parents[1]/'configs/research/nplayer-six-player-trajectory.json').read_text());study.validate_inventory(m)
        self.assertEqual(m['transfer_bytes'],7989712885);self.assertEqual(m['paired_hands'],786432)
        for bad in ['missing','unsafe','hash','scope','proof']:
            x=deepcopy(m)
            if bad=='missing':x['files'].pop()
            elif bad=='unsafe':x['files'][0]['name']='../bad'
            elif bad=='hash':x['files'][0]['sha256']='f'*64
            elif bad=='scope':x['panels'][0]['blocks']=2048
            else:x['files'][0]['proof']['status']='failed'
            with self.subTest(bad=bad),self.assertRaises(ValueError):study.validate_inventory(x)
    def test_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'existing';p.write_text('original')
            with self.assertRaises(FileExistsError):study.run(None,None,p)
            self.assertEqual(p.read_text(),'original')

    def tiny_panel(self,root):
        from scripts import nplayer_paired_evidence as e
        schedule=[[ (i+r)%6 for i in range(6)] for r in range(6)]+[[(r-i)%6 for i in range(6)] for r in range(6)]
        paths=[];files={};pins=['a'*64,'b'*64]
        for arm in range(2):
            name=str(arm)+'.jsonl';path=root/name;paths.append(name)
            h=dict(format='nplayer-privileged-policy-replay-v1',harness='nplayer-paired-v1',identity=dict(players=6,stacks=[10000]*6,small_blind=50,big_blind=100),blocks=2,hands=24,seed=77,schedule=schedule,distinct_policy_instances=6,policies=[dict(sha256=pins[arm])]+[dict(script='check-call')]*5)
            data=[]
            for block in range(2):
                for rotation,ids in enumerate(schedule):
                    actor=ids.index(0);row=fixture([['raise',300] if arm else ['call',0]],reward=0)
                    row.update(hand=len(data),block=block,permutation=rotation,identities=ids,button=block%6,actors=[actor])
                    row['states'][0]['actor']=actor;row['lookups'][0].update(identity=0,seat=actor,position=(actor-block)%6,street=0)
                    if arm:row['rewards'][actor]=100+block*200;row['rewards'][ids.index(1)]=-100-block*200
                    data.append(row)
            path.write_text('\n'.join(json.dumps(x) for x in [h,*data])+'\n');raw=path.read_bytes();files[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        panel=dict(contrast='10b-15b',field='tiny',files=paths,root=77,blocks=2,schedule=schedule,focal_sha256s=pins,reference_contrast=dict(mean_bb100=200,standard_error_bb100=100),reference_focal_coverage=[[[24,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]]]*2)
        return panel,files
    def test_streamed_scan_reconciles_every_hand_block_and_lookup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);panel,files=self.tiny_panel(root);r=study.scan_panel(panel,files,root)
            self.assertEqual((r['hands'],r['blocks'],r['mean_bb100'],r['standard_error_bb100']),(24,2,200,100))
            self.assertEqual(r,study.scan_panel(panel,files,root));self.assertEqual(r['first_divergences'],24)
    def test_corrupt_payload_field_and_reference_counts_fail_closed(self):
        for mutation in ['hash','fixed-field','mean','coverage']:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                root=Path(d);panel,files=self.tiny_panel(root)
                if mutation=='hash':
                    path=root/panel['files'][1];path.write_bytes(path.read_bytes().replace(b'"call"',b'"call" ',1));files[panel['files'][1]]['bytes']=path.stat().st_size
                elif mutation=='fixed-field':
                    path=root/panel['files'][1];lines=path.read_text().splitlines();h=json.loads(lines[0]);h['policies'][1]['script']='random';lines[0]=json.dumps(h);path.write_text('\n'.join(lines)+'\n');raw=path.read_bytes();files[panel['files'][1]]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                elif mutation=='mean':panel['reference_contrast']['mean_bb100']=201
                else:panel['reference_focal_coverage'][0][0][0]=23
                with self.assertRaises(ValueError):study.scan_panel(panel,files,root)


if __name__=='__main__':unittest.main()
