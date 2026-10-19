import json
from pathlib import Path
import pytest
from scripts import nplayer_bb100_confirmation as study
from scripts import run_nplayer_storage_benchmark as guard


def test_matrix_is_fixed_disjoint_and_paired():
    roots=[]
    for index in range(2):
        rows=study.matrix(index)
        assert len(rows)==18
        for a,b in zip(rows[::2],rows[1::2]):
            assert a['root']==b['root'] and a['blocks']==b['blocks']==8192
            roots.append(a['root'])
    cross=study.cross_cases()
    assert len(cross)==6
    for a,b in zip(cross[::2],cross[1::2]):
        assert a['root']==b['root'] and a['pair']==b['pair']
        assert a['seed'] != a['opponent_seed']
        roots.append(a['root'])
    assert len(set(roots))==21
    assert sum(x['blocks']*6 for r in [study.matrix(0),study.matrix(1),cross] for x in r)==2064384
    assert set(roots).isdisjoint(x['root'] for x in study.old.cases())
    assert set(roots).isdisjoint(x['root'] for r in [study.matrix(0,True),study.matrix(1,True),study.cross_cases(True)] for x in r)
    assert study.expected_loads(cross)==9


def test_family_intervals_and_margins_are_not_pointwise():
    x=study.adjusted([5.,10.,15.,20.],16)
    assert x['lower_family95']<x['lower95_bb100']<x['mean_bb100']
    assert x['upper_family95']>x['upper95_bb100']
    with pytest.raises(ValueError):study.adjusted([float('nan'),1],2)


def test_staging_preserves_bytes_and_records_restoration(tmp_path):
    root=tmp_path/'live';root.mkdir();cache=tmp_path/'cache'
    file=root/'seed'/'model.gz';file.parent.mkdir();file.write_bytes(b'checkpoint bytes')
    digest=guard.sha(file)
    study.stage_files(root,cache,[file])
    assert file.is_symlink() and guard.sha(file)==digest
    assert (cache/'seed/model.gz').read_bytes()==b'checkpoint bytes'
    row=json.loads((root/'relocations.jsonl').read_text())
    assert row['sha256']==digest and not row['drive_accepted']
    assert row['destination']==str(cache/'seed/model.gz')
    study.stage_files(root,cache,[file])
    assert len((root/'relocations.jsonl').read_text().splitlines())==1


def test_staging_rejects_external_paths_and_existing_partial(tmp_path):
    root=tmp_path/'live';root.mkdir();cache=tmp_path/'cache';cache.mkdir()
    external=tmp_path/'external';external.write_text('protected')
    with pytest.raises(ValueError):study.stage_files(root,cache,[external])
    with pytest.raises(ValueError):study.stage_files(root,cache,[root/'..'/'external'])
    own=root/'own';own.write_text('new');(cache/'own').write_text('partial')
    with pytest.raises(ValueError):study.stage_files(root,cache,[own])
    assert own.read_text()=='new' and not own.is_symlink()
    link=root/'other';link.symlink_to(external)
    with pytest.raises(ValueError):study.stage_files(root,cache,[link])
    assert external.read_text()=='protected'


def test_staging_failed_verification_retains_original(tmp_path,monkeypatch):
    root=tmp_path/'live';root.mkdir();cache=tmp_path/'cache';file=root/'data';file.write_text('evidence')
    real=guard.sha
    monkeypatch.setattr(guard,'sha',lambda path:'bad' if Path(path).is_relative_to(cache) else real(path))
    with pytest.raises(ValueError):study.stage_files(root,cache,[file])
    assert not file.is_symlink() and file.read_text()=='evidence'
    assert (cache/'data').read_text()=='evidence'
    assert not (root/'relocations.jsonl').exists()


def test_changed_science_rejected_before_build_access():
    c=dict(smoke=False,seeds=list(study.SEEDS),targets=list(study.TARGETS),cap=250000000,
        matrices=[study.matrix(0),study.matrix(1)],cross=study.cross_cases(),
        source_files={},resource_policy=study.prior.RESOURCE_POLICY)
    c['matrices'][0][0]['root']+=1
    with pytest.raises(ValueError,match='frozen confirmation'):study.validate_config(c)
