"""Independent arithmetic and fail-closed evidence checks; no poker model."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import summarize_river_exact as s
from scripts.qualify_river_exact import jobs,PANEL_SHA,SHA
from scripts.qualify_river_continuation import write,sha


def quality(v,g):return {'profile_values_bb':[v,-v],'best_response_gains_bb':g}


def value(q,bp,hero):
    worst=q['profile_values_bb'][hero]-q['best_response_gains_bb'][1-hero]
    bw=bp['profile_values_bb'][hero]-bp['best_response_gains_bb'][1-hero]
    return {'quality':q,'hero_worst_case_bb':worst,'blueprint_hero_worst_case_bb':bw,'hero_worst_case_change_bb':worst-bw}


def record(i,menu,backend):
    installed=i not in (137,195);hero=0;bp=quality(0.,[.3,.4]);digest=f'{i}/{menu}/{backend}'
    candidate=quality(1. if menu==s.MENUS[0] else .2,[.1,.5 if menu==s.MENUS[0] else .1])
    actual=candidate if installed else bp
    cap=quality(0.,[.01,.02] if installed else [.11,.19])
    laws={law:{'candidate_profile':value(candidate,bp,hero),'actual_deployed_policy':value(actual,bp,hero),'blueprint_quality':bp} for law in ('projected','exact_modeled')}
    return {'case_index':i,'menu':menu,'backend':backend,'original_projected_identity':backend!='exact-folded-prefix-v1',
        'begin':{'roundtrip_seconds':.3,'result':{'session':{'installed_search':installed,'binding':{'profile_sha256':digest,'retained_payload_bytes':100}},
            'sweeps':2048 if not installed else 64,'target_bb':.1,'quality':cap,'checkpoints':[{'sweeps':2048,'target_met':installed}]}},
        'continuation':{'result':{'solver_advances':0,'checked_rows':3 if installed else 0}},
        'audit':{'roundtrip_seconds':1.,'result':{'profile_sha256':digest,'solver_advances':0,'profile_unchanged':True,'installed_search':installed,
            'actual_policy':'search' if installed else 'blueprint-fallback','hero_game_seat':hero,'laws':laws,
            'capped_exact_oracle':{'dense_quality':cap,'max_error_bb':0.}}}}


def dump(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def fixture(root):
    root.mkdir();cal=root/'cal';cal.mkdir()
    write(root/'status.json',{'status':'complete','source':'frozen'})
    write(root/'launch.json',{'source':'frozen'})
    phases=[r+'-'+p for r in ('initial','repeat') for p in ('controls','projected','exact')]+['verify']
    write(root/'stage-costs.json',[{'phase':p,'returncode':0,'wall_seconds':1,'user_cpu_seconds':1,'system_cpu_seconds':0} for p in phases])
    write(root/'parent-pins.json',{'panel_sha256':PANEL_SHA,'model_sha256':SHA,'controls':list(range(20))})
    write(root/'calibration-pin.json',{'path':str(cal)})
    write(cal/'status.json',{'status':'complete','source':'frozen'})
    for p in (root,cal):
        write(p/'binary-pin.json',{'binary':'pin'});write(p/'source-manifest.json',{'file':'hash'})
    counts={}
    for phase in ('controls','projected','exact'):
        rows=([{'case_index':i,'status':'ok','result':{'max_leaf_error_bb':0.,'max_quality_error_bb':0.,
                'timings':{'prefix_fixed_solve_seconds':1.,'dense_fixed_solve_seconds':2.}}} for i in range(20)] if phase=='controls' else
              [record(i,m,b) for i,m,b in jobs(phase,range(200))])
        a=root/'initial'/phase/'records.jsonl';b=root/'repeat'/phase/'records.jsonl';dump(a,rows);dump(b,rows)
        counts[phase]={'records':len(rows),'initial_sha256':sha(a),'repeat_sha256':sha(b)}
    (root/'verification').mkdir();write(root/'verification/verified.json',{'status':'passed','counts':counts})
    dump(root/'resources.jsonl',[{'worker_family_rss_bytes':1024,'cpu_c':50.,'thermistor15_c':60.,'swap_used_bytes':100,
        'nvme_free_bytes':200,'hdd_free_bytes':300,'available_ram_bytes':400}])


def test_lower_deviation_gain_does_not_imply_better_absolute_worst_case(tmp_path):
    root=tmp_path/'input';fixture(root);out=s.readout(root)
    paired=out['comparisons']['menu_at_deployment_projected_law']
    assert paired['opponent_gain_reduction_bb']['median']==pytest.approx(.4)
    assert paired['hero_worst_case_change_bb']['median']==pytest.approx(-.4)
    assert paired['worse']==198 and paired['within_numeric_tolerance']==2
    assert out['arms']['expanded_exact']['fallbacks']==2
    assert out['original_misses'][0]['case_index']==137
    assert out['arms']['expanded_exact']['every_decision_declared_quality_gate'] is False


def test_readout_requires_complete_failure_free_verified_unchanged_evidence(tmp_path):
    root=tmp_path/'input';fixture(root)
    write(root/'failure.json',{'error':'preserved failure'})
    with pytest.raises(ValueError,match='failure-free'):s.readout(root)
    (root/'failure.json').unlink();write(root/'binary-pin.json',{'binary':'changed'})
    with pytest.raises(ValueError,match='qualified binary'):s.readout(root)
    write(root/'binary-pin.json',{'binary':'pin'})
    path=root/'initial/exact/records.jsonl';path.write_text(path.read_text()+'{}\n')
    with pytest.raises(ValueError,match='reproduction'):s.readout(root)


def test_costs_count_every_worker_load_without_treating_parallel_loads_as_wall(tmp_path):
    root=tmp_path/'input';fixture(root)
    for repetition in ('initial','repeat'):
        for phase,n in [('controls',1),('projected',5),('exact',5)]:
            write(root/repetition/phase/'startup.json',[{'status':'ready','model_sha256':SHA,
                'model_and_k50_load_seconds':120.,'policy_load_seconds':115.}]*n)
    costs=s.readout(root)['costs']
    assert costs['model_load_instances']==22
    assert costs['summed_worker_startup_seconds']==2640.
    assert costs['wall_seconds']==7.
    write(root/'initial/controls/startup.json',[{'status':'ready','model_sha256':'wrong'}])
    with pytest.raises(ValueError,match='startup model identity'):s.readout(root)
