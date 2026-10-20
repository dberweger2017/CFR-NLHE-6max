"""Controller boundaries: immutable restores, narrow trace equivalence, process costs."""
import json
from pathlib import Path
import sys
import pytest
from scripts import nplayer_inference_validation as study


def trace(path, sha='a', rows=None, header_change=None):
    h=dict(hands=2,policies=[dict(sha256=sha,source_checkpoint_sha256='fixed',strategy='average')])
    h.update(header_change or {})
    path.write_text('\n'.join(json.dumps(v) for v in [h,*(rows or [dict(hand=0),dict(hand=1)])])+'\n')


def test_trace_comparison_allows_only_artifact_pins(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b';trace(a);trace(b,'b')
    assert study.same_trace(a,b)==2
    trace(b,'b',header_change=dict(hands=3))
    with pytest.raises(ValueError):study.same_trace(a,b)
    trace(b,'b',rows=[dict(hand=0),dict(hand=2)])
    with pytest.raises(ValueError):study.same_trace(a,b)
    trace(b,'b',rows=[dict(hand=0)])
    with pytest.raises(ValueError):study.same_trace(a,b)


def test_pinned_restore_no_overwrite_and_failure_keeps_partial(tmp_path):
    a=tmp_path/'source';a.write_bytes(b'input')
    out=tmp_path/'out';study.copy_pinned(a,out,study.sha(a));assert out.read_bytes()==a.read_bytes()
    with pytest.raises(FileExistsError):study.copy_pinned(a,out,study.sha(a))
    bad=tmp_path/'bad'
    with pytest.raises(ValueError):study.copy_pinned(a,bad,'0'*64)
    assert bad.read_bytes()==b'input' and a.read_bytes()==b'input'


def test_child_reports_its_own_cost_and_preserves_failure(tmp_path):
    a=tmp_path/'good';a.mkdir()
    study.child(a,[sys.executable,'-c','print(123)'])
    value=study.load(a/'process.json')
    assert value['returncode']==0 and value['peak_rss_bytes']>0 and value['wall_seconds']>0
    b=tmp_path/'bad';b.mkdir()
    with pytest.raises(SystemExit):study.child(b,[sys.executable,'-c','raise SystemExit(7)'])
    assert study.load(b/'process.json')['returncode']==7
