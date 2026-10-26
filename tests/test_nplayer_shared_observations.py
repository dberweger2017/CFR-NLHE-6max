from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from scripts import nplayer_shared_observations as shared
from scripts import nplayer_paired_evidence as evidence


class SharedObservationsTests(unittest.TestCase):
    def fixture(self,root):
        n=4;schedule=evidence.seating(n);specs={};pins={}
        for alias,probabilities in [('control',[.75,.25]),('candidate',[.5,.5])]:
            folder=root/alias;folder.mkdir();policy=folder/'average.gz';zeros=folder/'zero-keys.bin'
            cp=('a' if alias=='control' else 'b')*64
            with gzip.open(policy,'wt') as f:
                f.write(json.dumps(dict(entries=n,source_checkpoint_sha256=cp))+'\n')
                for owner in range(n):f.write(json.dumps([f'{owner:032x}',owner,0,5,probabilities])+'\n')
            zero=alias=='candidate';zeros.write_bytes(b''.join(bytes.fromhex(f'{i:032x}') for i in range(n)) if zero else b'')
            receipt=folder/'receipt.json';receipt.write_text(json.dumps(dict(zero_keys_sha256=evidence.sha(zeros),zero_mass_rows=n if zero else 0)))
            pins[alias]=dict(sha256=evidence.sha(policy),mass_sha256=evidence.sha(receipt),source_checkpoint_sha256=cp)
            specs[alias]=dict(source_policy=str(policy),source_policy_sha256=evidence.sha(policy),mass=str(folder),mass_sha256=evidence.sha(receipt))
        paths=[];proofs=[]
        for arm,alias in enumerate(['control','candidate']):
            h=dict(format='nplayer-privileged-policy-replay-v1',harness='nplayer-paired-v1',identity=dict(players=n,stacks=[10000]*n,small_blind=50,big_blind=100),blocks=2,hands=8,seed=13,schedule=schedule,distinct_policy_instances=n,
                policies=[pins[alias]]+[dict(script='check-call')]*(n-1),shared_models=[dict(alias=k,pin=v) for k,v in pins.items()])
            data=[]
            for block in range(2):
                for rotation,ids in enumerate(schedule):
                    actor=ids.index(0);position=(actor-block%n)%n
                    state=dict(actor=actor,board=[],street='preflop',players=[[10000,0,0,False] for _ in range(n)],holes=[[i,i+4] for i in range(n)],legal=dict(check=False,call=100,raise_to=None))
                    row=dict(hand=len(data),block=block,permutation=rotation,identities=ids,button=block%n,deck=list(range(52)),stacks=[10000]*n,sb=50,bb=100,rewards=[0]*n,actors=[actor],actions=[['call',0]],states=[state,{}],history=[['preflop',actor,'call',0,100]],lookups=[dict(status='positive_mass' if arm==0 else 'zero_mass',identity=0,seat=actor,position=position,street=0,key=f'{position:032x}')])
                    row['lookups'][0]['shared']=dict(format='nplayer-shared-observation-v1',key=f'{position:032x}',observation_sha256=shared.fingerprint(row,0),actions=[['fold',0],['call',0]],queries=[dict(alias='control',status='positive_mass',probabilities=[.75,.25]),dict(alias='candidate',status='zero_mass',probabilities=[.5,.5])])
                    data.append(row)
            path=root/(alias+'.jsonl');path.write_text('\n'.join(json.dumps(z) for z in [h,*data])+'\n');proof=root/(alias+'-proof.json');proof.write_text(json.dumps(dict(status='passed',trace_sha256=evidence.sha(path),hands=8,players=n)));paths.append(path);proofs.append(proof)
        return paths[0],paths[1],paths[0],paths[1],proofs[0],proofs[1],specs

    def test_all_focal_occurrences_including_unchanged_actions_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));r=shared.verified_diagnostics(*args[:6])
            self.assertEqual((r['observations'],r['paired_queries']),(16,32));self.assertEqual(sum(r['block_counts'].values()),16)
            for g in r['groups'].values():self.assertEqual(g['mean_probability_tv'],.25);self.assertEqual(g['transition_counts'],{'positive_mass->zero_mass':8})

    def test_exact_source_audit_distinguishes_uniform_zero_and_absent(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));r=shared.audit_source_rows(args[:2],args[-1]);self.assertEqual(r['models'],2);self.assertTrue(r['exact_float64_source_rows'])

    def test_private_opponent_cards_deck_rewards_future_states_do_not_enter_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));row=list(evidence.rows(args[0]))[1];original=shared.fingerprint(row,0);actor=row['actors'][0]
            other=deepcopy(row);other['states'][0]['holes'][(actor+1)%4]=[50,51];other['deck']=list(reversed(other['deck']));other['rewards']=[10,-10,0,0];other['states'][-1]={'board':[40,41,42,43,44]}
            self.assertEqual(shared.fingerprint(other,0),original)
            other['states'][0]['hole']=[50,51] # Unused simulator field cannot enter projection.
            self.assertEqual(shared.fingerprint(other,0),original)
            other['states'][0]['holes'][actor]=[48,49];self.assertNotEqual(shared.fingerprint(other,0),original)

    def test_menu_deduplicates_conditional_jam_and_preserves_action_order(self):
        row=dict(states=[dict(players=[[9900,100,100,False]],legal=dict(check=True,call=0,raise_to=[200,10000]))],actors=[0])
        self.assertEqual(shared.menu(row,0),[(1,['check',0]),(3,['raise',200])])
        row['states'][0]['legal']['raise_to']=[200,300]
        self.assertEqual(shared.menu(row,0),[(1,['check',0]),(3,['raise',200]),(5,['raise',300])])

    def test_shared_fingerprint_menu_status_and_nonfinite_corruption_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));h,row=list(evidence.rows(args[0]))[:2]
            for mutate in ['fingerprint','menu','key','missing','status','nan','own']:
                bad=deepcopy(row);q=bad['lookups'][0]['shared']
                if mutate=='fingerprint':q['observation_sha256']='0'*64
                elif mutate=='menu':q['actions'].reverse()
                elif mutate=='key':q['key']='f'*32
                elif mutate=='missing':bad['lookups'][0].pop('shared')
                elif mutate=='status':q['queries'][0]['status']='unknown'
                elif mutate=='nan':q['queries'][0]['probabilities']=[float('nan'),.5]
                else:bad['lookups'][0]['status']='missing'
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):shared.query_rows(bad,0,h)

    def test_replay_reproduction_and_probability_source_barriers(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));proof=json.loads(args[4].read_text());proof['status']='failed';args[4].write_text(json.dumps(proof))
            with self.assertRaisesRegex(ValueError,'barrier'):shared.verified_diagnostics(*args[:6])
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));rows=list(evidence.rows(args[0]));rows[1]['lookups'][0]['shared']['queries'][0]['probabilities']=[.5,.5];args[0].write_text('\n'.join(json.dumps(z) for z in rows)+'\n')
            with self.assertRaisesRegex(ValueError,'source row differs|queried inconsistently'):shared.audit_source_rows(args[:2],args[-1])

    def test_diagnostics_off_parity_detects_action_rng_changes(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));values=list(evidence.rows(args[0]));values[0].pop('shared_models')
            for row in values[1:]:row['lookups'][0].pop('shared')
            other=Path(d)/'ordinary';other.write_text('\n'.join(json.dumps(z) for z in values)+'\n')
            self.assertTrue(shared.ordinary_payload_parity(args[0],other)['ordinary_trace_and_rng_unchanged'])
            values[1]['actions']=[['fold',0]];other.write_text('\n'.join(json.dumps(z) for z in values)+'\n')
            with self.assertRaisesRegex(ValueError,'action/RNG'):shared.ordinary_payload_parity(args[0],other)


if __name__=='__main__':unittest.main()
