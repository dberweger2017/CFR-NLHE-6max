from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_five_player_candidate as study
from scripts import plan_nplayer_five_player_candidate as pricing


class FivePlayerCandidateTests(unittest.TestCase):
    def test_fixed_game_targets_seating_counts_and_disjoint_fixture(self):
        c=study.fixed();q=study.fixed(True)
        self.assertEqual((c['players'],c['stack_bb'],c['seed']),(5,100,2026102351001))
        self.assertEqual(c['targets'],[3000000000,10000000000]);self.assertEqual(c['cap'],250000000)
        self.assertEqual(len(study.evidence.seating(5,c['schedule'])),10)
        self.assertEqual(c['blocks']*10*2*8,655360)
        self.assertFalse(set(range(c['root_base'],c['root_base']+8))&set(range(q['root_base'],q['root_base']+8)))
        self.assertNotEqual(c['seed'],q['seed']);self.assertEqual(q['targets'],[100000,200000])

    def test_only_focal_changes_and_all_opponents_are_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=dict(study.fixed(),tables='/tables');m=study.manifest(Path(tmp),c,{},'first')
            self.assertEqual(len(m['cases']),8)
            for row,field in zip(m['cases'],c['fields']):
                self.assertEqual(row['focals'],['baseline','candidate']);self.assertEqual(row['opponents'],field['opponents'])
                self.assertEqual(row['schedule'],c['schedule']);self.assertEqual(len(row['traces']),2)
            self.assertEqual(m['cases'][0]['opponents'],['baseline']*4)
            self_case=study.manifest(Path(tmp),c,{},'self',self_only=True)['cases'][0]
            self.assertEqual(self_case['focals'],['baseline','baseline'])

    def test_recipe_resume_and_no_extra_resource_cutoffs(self):
        c=dict(study.fixed(),tables='/tables',binaries={'nplayer_train':'train'})
        parent=dict(checkpoint='/prior',sha256='pinned')
        args=study.four.train_command(c,Path('/out'),10000000000,c['seed'],c['cap'],parent,16)
        for option,value in (('--players','5'),('--stack-bb','100'),('--threads','16'),('--seed','2026102351001'),('--max-entries','250000000'),('--roots-per-seat','8'),('--resume-sha256','pinned')):
            self.assertEqual(args[args.index(option)+1],value)
        self.assertIn('--freeze-at-cap',args);self.assertNotIn('--prune-bb',args)
        self.assertTrue(c['no_time_rss_disk_swap_stop']);self.assertEqual(args[args.index('--max-seconds')+1],'1e100')

    def test_wrong_budget_or_existing_root_cannot_prepare_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            with self.assertRaisesRegex(ValueError,'acceptance required'):study.configure(root,None,False,accepted=1)
            self.assertFalse(root.exists())
            root.mkdir()
            with self.assertRaises(FileExistsError):study.configure(root,None,False,accepted=21600)

    def test_duplicate_attempt_cannot_reach_validation_or_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);study.write(root/'launch.json',dict(pid=1))
            with patch.object(study,'validate') as v,patch.object(study,'execute') as e:
                with self.assertRaises(FileExistsError):study.run(root)
                v.assert_not_called();e.assert_not_called()

    def test_mutated_targets_recipe_seeds_counts_schedule_and_guards_refused(self):
        for key,value in [('targets',[3000000000]),('seed',2),('cap',300000000),('threads',8),('players',4),('stack_bb',200),('pruning',True),('schedule',study.SCHEDULE[:4]),('fields',[]),('blocks',8192),('no_time_rss_disk_swap_stop',False),('incomplete_policy','retry'),('interval_family','unadjusted')]:
            c=dict(study.fixed());c['fixed']=study.fixed();c[key]=value
            with self.subTest(key=key),patch.object(study,'source') as s:
                with self.assertRaisesRegex(ValueError,'scope changed'):study.validate(c)
                s.assert_not_called()

    def test_reproduction_failure_never_calls_statistical_readout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'a';b=root/'b';a.write_text('old');b.write_text('changed')
            class NoStages:
                def stage(self,*args):raise AssertionError('must reject before replay')
            with self.assertRaisesRegex(ValueError,'reproduction differs'):
                study.verify_case(root,{},NoStages(),dict(name='field',traces=[str(a)]),dict(traces=[str(b)]))

    def test_binary_gzip_parity_normalizes_only_audited_source_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b';models={'baseline':dict(sha256='binary',source_policy_sha256='gzip')}
            left={'identity':{'players':4},'policies':[{'sha256':'binary','mass_sha256':'mass'}]}
            right={'identity':{'players':4},'policies':[{'sha256':'gzip','mass_sha256':'mass'}]}
            a.write_text(json.dumps(left)+'\n'+json.dumps({'actions':['call']})+'\n')
            b.write_text(json.dumps(right)+'\n'+json.dumps({'actions':['call']})+'\n')
            study.trace_payload_parity(a,b,models)
            b.write_text(json.dumps(right)+'\n'+json.dumps({'actions':['fold']})+'\n')
            with self.assertRaisesRegex(ValueError,'payload differs'):study.trace_payload_parity(a,b,models)
            right['identity']['players']=3;b.write_text(json.dumps(right)+'\n')
            with self.assertRaisesRegex(ValueError,'header identity'):study.trace_payload_parity(a,b,models)

    def test_quote_is_metadata_only_complete_and_reproducible(self):
        q=pricing.proposal();committed=study.load(study.SOURCE/study.PROPOSAL)
        self.assertEqual(q,committed);self.assertEqual(q['initial_hands'],655360)
        self.assertEqual(q['reproduction_hands'],655360)
        self.assertAlmostEqual(sum(x['central_seconds'] for x in q['components']),q['central_seconds'])
        self.assertAlmostEqual(sum(x['reserved_seconds'] for x in q['components']),q['reserved_seconds'])
        self.assertGreaterEqual(q['proposed_allocation_seconds'],q['reserved_seconds'])
        self.assertEqual(q['proposed_allocation_seconds'],21600)
        self.assertIn('unmeasured',q['limits'])
        self.assertEqual(q['storage']['requested_free_bytes'],sum(q['storage'][k] for k in ('model_derivatives_scenario_bytes','all_trace_scenario_bytes','manual_headroom_bytes')))

    def test_forward_reverse_seatings_have_two_circular_orders_and_balance(self):
        schedule=study.SCHEDULE
        self.assertEqual(len({tuple(r) for r in schedule}),10)
        circular=set()
        for row in schedule:
            i=row.index(0);circular.add(tuple(row[(i+j)%5] for j in range(5)))
        self.assertEqual(circular,{(0,1,2,3,4),(0,4,3,2,1)})
        for identity in range(5):
            for seat in range(5):self.assertEqual(sum(r[seat]==identity for r in schedule),2)
            for button in range(5):
                self.assertEqual(sorted((r.index(identity)-button)%5 for r in schedule),[0,0,1,1,2,2,3,3,4,4])

    def test_five_player_ten_seatings_collapse_into_two_independent_deal_blocks(self):
        import statistics
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);c=study.fixed();schedule=c['schedule']
            header=dict(format='nplayer-privileged-policy-replay-v1',harness='nplayer-paired-v1',
                identity=dict(players=5,stacks=[10000]*5,small_blind=50,big_blind=100),
                blocks=2,hands=20,seed=123,schedule=schedule,policies=[{'script':'check-call'}]*5,distinct_policy_instances=5)
            left=[];right=[]
            for block in range(2):
                for rotation,ids in enumerate(schedule):
                    row=dict(hand=len(left),block=block,permutation=rotation,identities=ids,button=block%5,
                        deck=list(range(52)),stacks=[10000]*5,sb=50,bb=100,rewards=[0]*5,
                        lookups=[{'status':'not_applicable'}],actions=[['check',0]],actors=[0],states=[{'street':'preflop'},{}])
                    left.append(row);new=deepcopy(row);focal=ids.index(0)
                    delta=100*block+10*rotation
                    new['rewards'][focal]=delta;new['rewards'][(focal+1)%5]=-delta;right.append(new)
            paths=[]
            for name,data in (('a',left),('b',right)):
                h=deepcopy(header)
                if name=='b':h['policies'][0]={'script':'random'}
                trace=root/name;trace.write_text('\n'.join(json.dumps(z) for z in [h,*data])+'\n');paths.append(trace)
            proofs=[]
            for trace in paths:
                proof=root/(trace.name+'proof');proof.write_text(json.dumps(dict(status='passed',trace_sha256=study.sha(trace),hands=20,players=5)));proofs.append(proof)
            def stats(values):
                return dict(mean_bb100=statistics.mean(values),standard_error_bb100=statistics.stdev(values)/len(values)**.5)
            with patch.object(study.evidence,'interval',side_effect=stats):
                result=study.evidence.verified_pair(*paths,*paths,*proofs)
            self.assertEqual(result['blocks'],2)
            self.assertEqual(result['block_values_bb100'],[45,145])
            self.assertEqual(result['contrast'],dict(mean_bb100=95,standard_error_bb100=50))
            self.assertEqual(result['hands_per_arm'],20)

    def support_fixture(self):
        a=dict(rows=40,keyset_sha256='same',zero_mass_rows=10,
            by_street=[dict(entries=10,visits=20,zero_visit_entries=4) for _ in range(4)])
        b=deepcopy(a);b['zero_mass_rows']=6
        for street in b['by_street']:street.update(visits=50,zero_visit_entries=2)
        pair=dict(lookup_labels=study.evidence.LABELS,coverage=[dict(by_identity=[[[8,1,1,0]]*4]),dict(by_identity=[[[16,1,3,0]]*4])])
        return dict(baseline=dict(audit=a),candidate=dict(audit=b)),{'trained':pair}

    def test_support_deltas_keep_denominators_mass_and_membership_distinct(self):
        models,pairs=self.support_fixture();r=study.support_changes(models,pairs)
        self.assertEqual([s['added_visits'] for s in r['by_street']],[30]*4)
        self.assertEqual([s['net_zero_visit_row_reduction'] for s in r['by_street']],[2]*4)
        self.assertEqual(r['net_zero_average_mass_row_reduction'],4)
        rates=r['fields']['trained']['rate_change_10b_minus_3b'][3]
        self.assertAlmostEqual(rates['missing'],.05)
        self.assertAlmostEqual(rates['zero_mass'],-.05)
        self.assertEqual(r['fields']['trained']['focal_10b'][3]['decisions'],20)
        self.assertIn('not audited individual-row transitions',r['limitation'])

    def test_support_refuses_different_keys_street_membership_or_decreasing_visits(self):
        for mutation in ('keyset','entries','visits','streets'):
            models,pairs=self.support_fixture();b=models['candidate']['audit']
            if mutation=='keyset':b['keyset_sha256']='different'
            elif mutation=='entries':b['by_street'][0]['entries']=9
            elif mutation=='visits':b['by_street'][0]['visits']=19
            else:b['by_street'].pop()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):study.support_changes(models,pairs)

    def test_partial_failed_evidence_never_creates_global_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);c=study.fixed();c['tables']='/tables'
            for name,data in (('config',c),('evaluation-verified',{'status':'failed'}),('initial-manifest',{}),('repeat-manifest',{}),('verified-summary',{})):
                study.write(root/(name+'.json'),data)
            with patch.object(study,'validate'):
                with self.assertRaisesRegex(ValueError,'global frozen scope/proof'):study.summarize(root)
            self.assertFalse((root/'results.json').exists())
            (root/'failure.json').write_text('{}')
            with patch.object(study,'validate'):
                with self.assertRaisesRegex(ValueError,'failed or already'):study.summarize(root)

    def test_closeout_never_automatically_replicates_or_turns_partial_into_acceptance(self):
        gates=[dict(name=name,passed=True) for name,_ in study.FIELDS]
        self.assertEqual(study.development_decision(gates,False)['direction'],'consider-independent-five-player-lineages')
        gates[1]['passed']=False
        r=study.development_decision(gates,False)
        self.assertEqual(r['direction'],'review-scripted-exploitation-tradeoff-before-replication');self.assertTrue(r['no_automatic_followup'])
        gates[0]['passed']=False
        self.assertEqual(study.development_decision(gates,False)['direction'],'review-support-and-recipe-before-further-allocation')
        with self.assertRaisesRegex(ValueError,'incomplete'):study.development_decision(gates[:-1],False)

    def test_quote_scales_only_hand_work_and_prices_loading_independently(self):
        q=pricing.proposal();components={r['name']:r for r in q['components']}
        prior=study.load(study.SOURCE/pricing.INPUT)
        loads=sum(c['load_seconds'] for phase in prior['arena_costs'].values() for c in phase.values())
        self.assertAlmostEqual(components['two arena model loads']['central_seconds'],loads*1.25)
        self.assertEqual(q['assumptions']['seating_hand_ratio'],10/24)
        self.assertLess(q['central_seconds'],3*3600);self.assertGreater(q['central_seconds'],2.5*3600)
        self.assertEqual(q['proposed_allocation_seconds'],6*3600)


if __name__=='__main__':unittest.main()
