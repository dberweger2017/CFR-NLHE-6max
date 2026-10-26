import copy
from scripts.qualify_river_continuation import control_selection,solve_request,control_request,stable,expected
import pytest


def cases(pots):
    return [dict(panel='fixed',hand=i,request={'players':[[0,0,int(p*100),False]]}) for i,p in enumerate(pots)]


def test_stratified_selection_is_stable_unique_and_fills_underfull_bands():
    rows=cases([2]*3+[10]*10+[20]*10+[50]*10)
    a=control_selection(rows)
    assert a==control_selection(copy.deepcopy(rows))
    assert len(a['case_indices'])==len(set(a['case_indices']))==20
    assert a['selected_band_counts'][0]==3
    assert all(n>=5 for n in a['selected_band_counts'][1:])
    for row in rows:row['unread_outcome']=1e100
    assert control_selection(rows)==a


def test_quality_targets_are_explicit_and_belief_budgets_match():
    c=cases([10])[0]
    strict=solve_request(c,'strict','candidate')
    deployment=solve_request(c,'deployment','candidate')
    assert strict['sweeps']==8192 and strict['omitted']
    assert deployment['sweeps']==2048 and not deployment['omitted']
    control=control_request(c)
    assert control['matched_accuracy'] is True
    assert control['checkpoints']==control['reference_checkpoints']
    assert control['reference_tolerance_bb']==0.01


def test_reproduction_ignores_clocks_and_handles_but_preserves_strategy_and_quality():
    a={'timings':{'x':1},'roundtrip_seconds':2,'session':{'handle':'process-a','profile_sha256':'abc'},
       'quality':{'best_response_gains_bb':[.01,.02]},'probabilities':[.2,.8]}
    b=copy.deepcopy(a);b['timings']['x']=3;b['session']['handle']='process-b'
    assert stable(a)==stable(b)
    b['probabilities'][0]=.3
    assert stable(a)!=stable(b)
    b=copy.deepcopy(a);b['quality']['best_response_gains_bb'][0]=.1
    assert stable(a)!=stable(b)


def test_only_predeclared_support_failures_are_accepted():
    expected({'status':'unsupported','reason':'own holding has zero modeled root reach'})
    with pytest.raises(RuntimeError):expected({'status':'unsupported','reason':'retained payment differs'})
