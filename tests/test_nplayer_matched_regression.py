import copy
import hashlib
import json
import pytest
from scripts.nplayer_matched_regression import legal_state,readout


def row():
    return dict(identities=[1,0,2],button=0,block=10,permutation=2,actors=[0,1],actions=[['call',0],['raise',300]],
        states=[dict(actor=0,street='preflop',holes=[[0,1],[2,3],[4,5]],board=[]),dict(actor=1,street='preflop',holes=[[0,1],[2,3],[4,5]],board=[]),dict(actor=2,street='flop',holes=[[0,1],[2,3],[4,5]],board=[6,7,8])],
        lookups=[dict(key='0'*32),dict(key='1'*32)],deck=list(range(52)),rewards=[100,-50,-50])


def project(r,policy='baseline'):
    return legal_state(r,1,seed=202610200601,field='random-tight',reached=policy,root=20261020610009)


def test_projection_ignores_other_holes_future_cards_deck_and_outcomes():
    a=row();b=copy.deepcopy(a);b['deck']=list(reversed(b['deck']));b['rewards']=[-100,50,50]
    b['states'][1]['holes'][0]=[40,41];b['states'][1]['holes'][2]=[42,43];b['states'][2]['board']=[44,45,46]
    assert project(a)==project(b)
    s=project(a);assert s['hole']==[2,3] and s['board']==[] and s['actions']==[[0,'call',0]]
    assert s['opponents']==['random','hero','tight-aggressive']
    assert not set(s)&{'deck','rewards','opponent_holes','future_board'}
    assert project(a,'candidate')['split']==s['split']
    a['states'][1]['holes'][1]=[50,51];assert project(a)!=s


def write_fixture(folder,worlds=512):
    r=dict(matched=dict(state=dict(id='state',stratum='test',split='discovery'),probabilities=[[1.,0.],[0.,1.]],
        actions=[['fold',0],['call',0]],total_variation=1.,statuses=['positive_mass']*2),selected_action_index=1,belief=dict(tag_supported_holdings=None))
    (folder/'manifest.json').write_text('{}')
    (folder/'matched.jsonl').write_text(json.dumps(r['matched'])+'\n')
    (folder/'selected.jsonl').write_text(json.dumps(r)+'\n')
    with (folder/'values.jsonl').open('w') as f:
        for i in range(worlds):
            z=(i%2)-.5;f.write(json.dumps(dict(state_id='state',world=i,q=[[z,z+1],[z,z+1]],showdown_share=.75))+'\n')
    native=dict(status='passed',manifest_sha256=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest())
    for k in ('matched','selected','values'):native[k+'_sha256']=hashlib.sha256((folder/(k+'.jsonl')).read_bytes()).hexdigest()
    (folder/'native-result.json').write_text(json.dumps(native))


def test_paired_world_uncertainty_preserves_covariance(tmp_path):
    write_fixture(tmp_path);r=readout(tmp_path)
    assert r['status']=='settled' and len(r['panel'])==2 and r['family_size_upper_bound']==512
    for v in r['panel']:
        c=v['mixture_candidate_minus_baseline_bb'];assert c['mean']==c['normal_lower']==c['normal_upper']==1. and c['standard_error']==0. and c['lower']<1<c['upper']
        assert v['selected_minus_candidate_bb']['mean']==0.
        assert sum(v['contributions_bb'])==1.


def test_incomplete_worlds_or_modified_outputs_refuse(tmp_path):
    write_fixture(tmp_path,511)
    with pytest.raises(ValueError,match='incomplete'):readout(tmp_path)
    (tmp_path/'values.jsonl').write_text('changed')
    with pytest.raises(ValueError,match='changed'):readout(tmp_path)
