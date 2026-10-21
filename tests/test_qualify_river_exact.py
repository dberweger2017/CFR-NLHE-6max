"""Accounting/orchestration checks use artificial data, never mature models."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import qualify_river_exact as q


def old():
    return {'result':{'actions':[['check',0]],'probabilities':[1.],
        'sweeps':2048,'requested_sweeps':2048,'target_bb':.1,
        'quality':{'best_response_gains_bb':[.11,.19]},'search_menu':q.MENUS[1],'nodes':51,
        'checkpoints':[{'sweeps':2048,'target_met':False,'elapsed_seconds':1.}]}}


def begin():
    r=copy.deepcopy(old()['result']);r['produced_root_strategy']={k:r[k] for k in ('probabilities','actions')}
    # An unconverged retained begin actually returns the blueprint action.
    r['probabilities']=[.25,.75];r['actions']=[['check',0],['raise',100]]
    r['checkpoints'][0]['elapsed_seconds']=2.
    r['session']={'hand_id':'panel/1','handle':'opaque','binding':{'profile_sha256':'profile'},'installed_search':False}
    return {'status':'ok','result':r}


def test_original_identity_uses_produced_profile_not_blueprint_fallback():
    assert q.original_identity(begin(),old())
    for key in ('sweeps','quality'):
        changed=begin();changed['result'][key]=None
        with pytest.raises(RuntimeError,match='changed'):q.original_identity(changed,old())
    changed=begin();changed['result']['produced_root_strategy']['probabilities']=[.9,.1]
    with pytest.raises(RuntimeError,match='changed'):q.original_identity(changed,old())


def test_audit_runs_after_begin_on_the_same_session_and_never_requests_more_sweeps():
    class Worker:
        def __init__(self):self.requests=[]
        def ask(self,r):
            self.requests.append(copy.deepcopy(r));mode=r['mode']
            if mode=='retained-begin':return begin()
            assert (r['hand_id'],r['handle'])==('panel/1','opaque')
            return {'status':'ok','result':{'profile_sha256':'profile','solver_advances':0}}
    worker=Worker()
    result=q.panel_one(worker,{'panel':'panel','hand':1,'request':{}},q.MENUS[1],'projected-product-v1',old())
    assert result['original_projected_identity']
    assert [r['mode'] for r in worker.requests]==['retained-begin','retained-audit','retained-full-menu-audit','retained-release']
    assert worker.requests[0]['observation']['checkpoints']==[8,16,32,64,128,256,512,1024,2048]
    assert all('checkpoints' not in r and 'sweeps' not in r for r in worker.requests[1:])


def write_records(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def fixture(root):
    for phase in ('controls','projected','exact'):
        rows=([{'case_index':i,'value':i,'roundtrip_seconds':1.,'handle':'old'} for i in range(20)] if phase=='controls' else
              [{'case_index':i,'menu':m,'backend':b,'value':i,'roundtrip_seconds':1.,'handle':'old'} for i,m,b in q.jobs(phase,range(200))])
        write_records(root/'initial'/phase/'records.jsonl',rows)
        for r in rows:r.update(roundtrip_seconds=2.,handle='new')
        write_records(root/'repeat'/phase/'records.jsonl',rows)


def test_reproduction_excludes_only_clocks_handles_and_rejects_strategic_changes(tmp_path):
    fixture(tmp_path/'input')
    q.verify(SimpleNamespace(inputs=tmp_path/'input',out=tmp_path/'verified'))
    assert json.loads((tmp_path/'verified/verified.json').read_text())['counts']['projected']['records']==400
    path=tmp_path/'input/repeat/exact/records.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
    rows[137]['value']=-1;write_records(path,rows)
    with pytest.raises(RuntimeError,match='strategic reproduction'):q.verify(SimpleNamespace(inputs=tmp_path/'input',out=tmp_path/'bad'))


def test_reproduction_rejects_missing_or_duplicate_panel_work(tmp_path):
    fixture(tmp_path/'input')
    for part in ('initial','repeat'):
        path=tmp_path/f'input/{part}/exact/records.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
        rows[137]=rows[136];write_records(path,rows)
    with pytest.raises(RuntimeError,match='identities'):q.verify(SimpleNamespace(inputs=tmp_path/'input',out=tmp_path/'bad'))
