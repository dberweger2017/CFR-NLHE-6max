"""Small deterministic reader benchmark; never trains or retrieves research models.

Uses a fresh output directory, Unix wait4 per-process accounting, ordinary caches
and an explicit ABABAB load order. Fixture results are not mature-model forecasts.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import random
import statistics
import platform
import sys
import time

PINNED = [
    '084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
    'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
    '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629',
]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(binary, out, label, *args):
    start = time.monotonic()
    with (out / (label + '.stdout')).open('xb') as stdout, (out / (label + '.stderr')).open('xb') as stderr:
        pid = os.posix_spawn(str(binary), [str(binary), *map(str, args)], os.environ,
            file_actions=[(os.POSIX_SPAWN_DUP2, stdout.fileno(), 1), (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2)])
        _, status, usage = os.wait4(pid, 0)
    wall = time.monotonic() - start
    code = os.waitstatus_to_exitcode(status)
    if code:
        raise RuntimeError(f'{label} exited {code}; partial output retained at {out}')
    result = json.loads((out / (label + '.stdout')).read_text())
    return dict(result=result, wall_seconds=wall, cpu_seconds=usage.ru_utime + usage.ru_stime,
        peak_rss_bytes=usage.ru_maxrss if sys.platform == 'darwin' else usage.ru_maxrss * 1024,
        minor_faults=usage.ru_minflt, major_faults=usage.ru_majflt,
        block_inputs=usage.ru_inblock, block_outputs=usage.ru_oublock)


def fixture(path, rows):
    identity = dict(schema='nplayer-nlhe-cash-ordered-history-equity-k50-v1', game='nlhe-cash', players=3,
        stacks=[10000]*3, small_blind=50, big_blind=100, menu='hu-v1', card_tables=PINNED, utility_unit='big-blind')
    # Read names from native source rather than silently benchmark an obsolete schema.
    native = Path(__file__).resolve().parents[1] / 'native/hu20-trainer/src/multi_holdem.rs'
    import re
    source = native.read_text()
    for name, field in [('SCHEMA', 'schema'), ('MENU', 'menu')]:
        identity[field] = re.search(r'pub const ' + name + r': &str = "([^"]+)";', source)[1]
    header = dict(format='nplayer-policy-v1', identity=identity, players=3, entries=rows,
        strategy='average', last_average_street=3, continuation='none', missing='uniform', source_checkpoint_sha256='a'*64)
    keys = sorted(hashlib.blake2b(i.to_bytes(8,'little'),digest_size=16).digest() for i in range(rows))
    rng = random.Random(20261020359)
    with path.open('xb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed, io.TextIOWrapper(compressed) as stream:
        stream.write(json.dumps(header, separators=(',',':'))+'\n')
        for i,key in enumerate(keys):
            code = [3,6,15,31,63][i%5];n = code.bit_count()
            weights = [rng.random() for _ in range(n)]
            if i%11==0: weights = [1.]*n
            if i%17==0: weights[0] = 0.
            total = sum(weights)
            p = [w/total for w in weights]
            stream.write(json.dumps([key.hex(),i%3,i%4,code,p],separators=(',',':'))+'\n')
    return keys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--rows',type=int,default=100000)
    a=p.parse_args()
    if not 1000<=a.rows<=1000000: p.error('local fixture bound: 1000..1000000 rows')
    if not hasattr(os,'wait4'):p.error('Unix wait4 accounting required')
    binary=a.binary.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    source=out/'fixture.gz';target=out/'fixture.bin';keys=fixture(source,a.rows);pin=sha(source)
    conversion=run(binary,out,'conversion','convert',source,pin,target)
    binary_pin=sha(target)
    audit=run(binary,out,'full-row-audit','verify',source,pin,target,binary_pin)
    loads=[]
    for i,(path,pinned) in enumerate([(source,pin),(target,binary_pin)]*3):
        loads.append(run(binary,out,f'load-{i}','load',path,pinned))
    profile=run(binary,out,'json-profile','load',source,pin,'--profile')
    queries=out/'queries.json'
    # The same sorted samples and explicit missing keys reach both readers.
    sample=[keys[i].hex() for i in range(0,len(keys),max(1,len(keys)//4096))][:4096]
    sample += [hashlib.sha256(f'missing-{i}'.encode()).digest()[:16].hex() for i in range(64)]
    queries.write_text(json.dumps(sample)+'\n')
    probes=[run(binary,out,'probe-'+name,'probe',path,pinned,queries,32)
        for name,path,pinned in [('json',source,pin),('binary',target,binary_pin)]]
    assert probes[0]['result']['probe_sha256']==probes[1]['result']['probe_sha256']
    assert probes[0]['result']['found']==probes[1]['result']['found']
    medians={name:statistics.median(v['result']['total_seconds'] for v in loads if v['result']['format']==name)
        for name in ('gzip-json','binary')}
    receipt=dict(status='passed',rows=a.rows,binary_sha256=sha(binary),source_sha256=pin,derivative_sha256=binary_pin,
        platform=sys.platform,hardware=platform.machine(),python=platform.python_version(),
        execution_sources={str(path.relative_to(Path(__file__).resolve().parents[1])):sha(path)
            for path in [Path(__file__).resolve(), *[Path(__file__).resolve().parents[1]/name for name in (
                'native/hu20-trainer/src/multi_binary.rs','native/hu20-trainer/src/multi_policy.rs',
                'native/hu20-trainer/examples/nplayer_inference.rs','native/hu20-trainer/Cargo.lock')]]},
        conversion=conversion,audit=audit,load_order='ABABAB (A=gzip JSON, B=binary)',loads=loads,
        profiled_json=profile,probes=probes,median_load_seconds=medians,
        warm_load_speedup=medians['gzip-json']/medians['binary'],
        files={path.name:dict(bytes=path.stat().st_size,allocated_bytes=path.stat().st_blocks*512) for path in (source,target)},
        cache_note='Ordinary filesystem cache; conversion/audit touched both inputs before loads. First recorded loads are not cold-cache claims.',
        limits='Generated rows, one laptop, no real K50 play or mature-table performance claim; trajectory unit tests use explicit toy card assignments.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','rows','median_load_seconds','warm_load_speedup','files')},indent=2))


if __name__=='__main__':main()
