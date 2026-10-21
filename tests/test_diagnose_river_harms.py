"""Profile/old-result identity and non-adaptive cost accounting; no poker model."""
import copy
import json
from types import SimpleNamespace

import pytest
from scripts import diagnose_river_harms as h
from scripts.qualify_river_continuation import write


def begin():
    r={'actions':[['check',0]],'probabilities':[1.],'produced_root_strategy':{'probabilities':[1.]},
       'algorithm':'dcfr-1.5-0-2','sweeps':2048,'requested_sweeps':2048,'target_bb':.1,'nodes':39,
       'quality':{'profile_values_bb':[0.,0.],'best_response_gains_bb':[.1,.2]},
       'checkpoints':[{'sweeps':2048,'elapsed_seconds':1.,'target_met':False}],
       'session':{'installed_search':False,'binding':{'profile_sha256':'frozen'}}}
    return {'result':r}


def test_reconstruction_does_not_replace_original_misses_or_profile_bits():
    r=begin();ref={'begin':copy.deepcopy(r)}
    r['result']['checkpoints'][0]['elapsed_seconds']=99.
    h.original_identity(r,ref)
    for key,value in [('sweeps',4096),('quality',{}),('produced_root_strategy',{'probabilities':[.5,.5]})]:
        changed=copy.deepcopy(r);changed['result'][key]=value
        with pytest.raises(ValueError,match='reconstruction differs'):h.original_identity(changed,ref)
    changed=copy.deepcopy(r);changed['result']['session']['binding']['profile_sha256']='replacement'
    with pytest.raises(ValueError,match='binding differs'):h.original_identity(changed,ref)


def test_audits_cannot_substitute_another_profile_or_actual_policy():
    q={'profile_values_bb':[0.,0.],'best_response_gains_bb':[.2,.3]}
    metric={'quality':q,'hero_worst_case_bb':-.3}
    r={'profile_sha256':'frozen','profile_unchanged':True,'solver_advances':0,'installed_search':False,'actual_policy':'blueprint-fallback',
       'actual':{'metrics':metric,'responses':[]},'produced':{'metrics':metric,'responses':[]},'blueprint':{'quality':q}}
    old={'audit':{'result':{**{k:r[k] for k in ['profile_sha256','profile_unchanged','installed_search','actual_policy']},
        'laws':{'exact_modeled':{'actual_deployed_policy':metric,'candidate_profile':metric,'blueprint_quality':q}}}}}
    h.check_audit(r,old)
    for key,value in [('profile_sha256','different'),('solver_advances',1),('actual_policy','search')]:
        changed=copy.deepcopy(r);changed[key]=value
        with pytest.raises(ValueError):h.check_audit(changed,old)
    changed=copy.deepcopy(r);changed['produced']['metrics']['quality']['best_response_gains_bb'][1]=.4
    with pytest.raises(ValueError,match='aggregate'):h.check_audit(changed,old)


def test_fixed_matrix_preserves_both_fallbacks_and_no_outcome_selected_additions():
    rows=[{'case_index':i,'arm':a} for i in h.CASES for a,_,_ in h.ARMS]
    h.validate_manifest(rows)
    assert 137 in h.CASES and 195 in h.CASES and len(rows)==24
    with pytest.raises(ValueError,match='fixed snapshot matrix'):h.validate_manifest(rows+[rows[0]])
    with pytest.raises(ValueError,match='fixed snapshot matrix'):h.validate_manifest(rows[::-1])


def test_quote_includes_three_loads_all_reconstructions_and_two_audit_passes(tmp_path,monkeypatch):
    calibration=tmp_path/'cal';calibration.mkdir()
    rows=[{'case_index':0,'arm':a,'roundtrip_seconds':10.,'result':{'full_menu_nodes':100}} for a,_,_ in h.ARMS]
    (calibration/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write(calibration/'startup.json',{'model_and_k50_load_seconds':120.})
    old={(i,m,b):{'begin':{'roundtrip_seconds':1.},'audit':{'result':{'full_menu_nodes':100}}} for i in h.CASES for _,m,b in h.ARMS}
    monkeypatch.setattr(h,'inputs',lambda *_:(None,old))
    out=tmp_path/'quote';h.quote(SimpleNamespace(capture=calibration,out=out,parent=None,panel=None))
    q=json.loads((out/'quote.json').read_text())
    assert q['capture_prior_seconds']==24.
    assert q['one_audit_pass_estimate_seconds']==240.
    assert q['lower_seconds']==3*120+24+2*240
    assert q['upper_seconds']>q['lower_seconds']
    assert q['no_main_started'] is True
