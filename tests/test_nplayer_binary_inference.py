"""Exercise the explicit converter/reader CLI without research models or K50 files."""
import json
from pathlib import Path
import subprocess
import pytest
from scripts.benchmark_nplayer_inference import fixture, sha

BINARY=Path('native/hu20-trainer/target/release/examples/nplayer_inference').resolve()
pytestmark=pytest.mark.skipif(not BINARY.exists(),reason='build nplayer_inference')


def run(*args,code=0):
    r=subprocess.run([str(BINARY),*map(str,args)],capture_output=True,text=True,timeout=30)
    assert r.returncode==code,r.stderr
    return json.loads(r.stdout) if code==0 else r


def test_cli_exact_rows_pins_profile_and_no_overwrite(tmp_path):
    source=tmp_path/'source.gz';fixture(source,2000);pin=sha(source)
    out=tmp_path/'policy.bin';r=run('convert',source,pin,out)
    assert r['rows']==2000 and r['metadata']['source_policy_sha256']==pin
    assert run('verify',source,pin,out,sha(out))['rows']==2000
    a=run('load',source,pin,'--profile');b=run('load',out,sha(out))
    assert a['identity']==b['identity'] and a['rows']==b['rows']==2000
    assert a['stream_decode_seconds']>0 and a['parse_validate_allocate_seconds']>0
    assert a['index_insert_seconds']>0 and a['verify_file_seconds']>0
    original=out.read_bytes();run('convert',source,pin,out,code=2)
    assert out.read_bytes()==original
    run('verify',source,'0'*64,out,sha(out),code=2)
    run('load',out,'0'*64,code=2)
    assert out.read_bytes()==original


def test_cli_corrupt_artifact_refuses_even_with_its_actual_outer_hash(tmp_path):
    source=tmp_path/'source.gz';fixture(source,1000)
    binary=tmp_path/'policy.bin';run('convert',source,sha(source),binary)
    data=bytearray(binary.read_bytes());data[-1]^=1;binary.write_bytes(data)
    r=run('load',binary,sha(binary),code=2)
    assert 'checksum' in r.stderr


def test_small_benchmark_reports_each_process_and_identical_probes(tmp_path):
    out=tmp_path/'benchmark'
    r=subprocess.run(['python3.11','-m','scripts.benchmark_nplayer_inference','--binary',str(BINARY),'--out',str(out),'--rows','1000'],capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stderr
    v=json.loads((out/'receipt.json').read_text())
    assert v['status']=='passed' and len(v['loads'])==6
    assert [r['result']['format'] for r in v['loads']]==['gzip-json','binary']*3
    assert v['probes'][0]['result']['probe_sha256']==v['probes'][1]['result']['probe_sha256']
    assert all(r['peak_rss_bytes']>0 and r['minor_faults']>0 for r in v['loads'])
    assert v['conversion']['wall_seconds']>0 and v['audit']['result']['rows']==1000
