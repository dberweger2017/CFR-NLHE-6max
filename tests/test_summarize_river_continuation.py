"""Artificial readout fixtures check orientation and incomplete-evidence refusal."""
import copy
import json
import pytest

from scripts.qualify_river_continuation import MENUS,SHA,sha,write
from scripts.summarize_river_continuation import readout


def fixture(root):
    root.mkdir()
    write(root/'status.json',{'status':'complete'})
    (root/'verification').mkdir();write(root/'verification/verified.json',{'status':'passed'})
    write(root/'stage-costs.json',[{'phase':str(i),'returncode':0,'wall_seconds':1,'user_cpu_seconds':1,'system_cpu_seconds':0} for i in range(16)])
    (root/'panel').mkdir()
    cases=[{'panel':'fixture','hand':i,'request':{'seat':1,'players':[[0,0,100,False],[0,0,100,False],[0,0,0,True]]}} for i in range(200)]
    write(root/'panel/cases.json',{'cases':cases})
    write(root/'panel/freeze.json',{'model_sha256':SHA,'cases_sha256':sha(root/'panel/cases.json'),
          'source':'fixture-only','composition':[],'controls':{'case_indices':list(range(20))}})
    phases={p:[] for p in ['strict','deployment','retained','belief']}
    for i in range(200):
        for m,opp in zip(MENUS,[.4,.3]):
            # Hero is game player 1. The opponent metric is element 0 even
            # though candidate's maximum gain is much larger.
            result={'checkpoints':[{'target_met':i!=0}],'law':{'fixed':True},'nodes':10,'solver_memory_bytes':800,
                    'omitted_raise_evaluation':{'hero_game_seat':1,'quality':{'best_response_gains_bb':[opp,9.]},
                       'blueprint_only_quality':{'best_response_gains_bb':[.2,.1]},'seconds':.1}}
            phases['strict'].append({'case_index':i,'phase':'strict','menu':m,'status':'ok','roundtrip_seconds':.5,'result':result})
            result={'checkpoints':[{'target_met':True}],'probabilities':[.2,.8],'actions':[['check',0],['raise',100]],
                    'quality':{'best_response_gains_bb':[.01,.01]},'sweeps':64}
            phases['deployment'].append({'case_index':i,'phase':'deployment','menu':m,'status':'ok','roundtrip_seconds':.3,'result':result})
        begin=copy.deepcopy(phases['deployment'][-1]);installed=i!=199
        begin['result']['session']={'model_sha256':SHA,'hand_id':f'fixture/{i}','installed_search':installed,
            'fallback_reason':None if installed else 'nonconverged','binding':{'profile_sha256':'fixture-profile' if installed else None,'retained_payload_bytes':800}}
        phases['retained'].append({'case_index':i,'phase':'retained','menu':MENUS[1],'begin':begin,
            'audit':{'result':{'installed_search':installed,'checked_rows':2 if installed else 0,'solver_advances':0,'seconds':.001,'profile_sha256':'fixture-profile'}},
            'release':{'result':{'released':True}}})
    for i in range(20):
        phases['belief'].append({'case_index':i,'phase':'belief','status':'ok','roundtrip_seconds':1,
            'result':{'matched_accuracy':True,'target_bb':.01,'reference':{'tolerance_bb':.01,'sweeps':128},
            'deployed':{'sweeps':128},'decomposition':{'same_profile_law_shift_bb':[.02,.03],
            'solver_residual_bb':[.01,.01],'reference_residual_bb':[.005,.005]},
            'excess_gain_bb':[.025,.035],'qualified':i!=0,'passes':True,'pot_bb':2,'law':{'projection_total_variation':.03}}})
    for repeat in ['initial','repeat']:
        for phase,rows in phases.items():
            p=root/repeat/phase;p.mkdir(parents=True)
            (p/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    for i in range(2):
        (root/f'panel/classification-{i}.jsonl').write_text((json.dumps({'result':{'supported':True}})+'\n')*100)
    (root/'resources.jsonl').write_text(json.dumps({'worker_family_rss_bytes':100,'cpu_c':60,'thermistor15_c':70,
        'available_ram_bytes':1000,'swap_used_bytes':350,'nvme_free_bytes':10000,'hdd_free_bytes':100000})+'\n')


def test_orientation_unqualified_pairs_and_inconclusive_controls_are_preserved(tmp_path):
    root=tmp_path/'fixture';fixture(root);r=readout(root)
    assert r['primary']['qualified_pairs']==199
    assert r['primary']['inconclusive_pairs']==1
    assert r['primary']['paired_opponent_gain_reduction_bb']['median']==pytest.approx(.1)
    assert r['belief']['verdict']=='inconclusive' and r['belief']['qualified']==19
    assert r['retained']['installed']==199 and r['retained']['fallbacks']==1
    assert r['retained']['solver_advances']==0


def test_duplicate_case_and_unverified_or_failed_study_refuse(tmp_path):
    root=tmp_path/'fixture';fixture(root)
    p=root/'initial/strict/records.jsonl'
    rows=[json.loads(s) for s in p.read_text().splitlines()];rows[1]=copy.deepcopy(rows[0])
    for rep in ['initial','repeat']:(root/rep/'strict/records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError,match='duplicated'):readout(root)
    write(root/'failure.json',{'error':'fixture terminal failure'})
    with pytest.raises(ValueError,match='not complete'):readout(root)
