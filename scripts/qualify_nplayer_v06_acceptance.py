"""Small isolated fixture creator. Does not configure or launch final acceptance."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from scripts import benchmark_nplayer_inference as benchmark
from scripts import nplayer_inference_validation as io
from scripts.nplayer_v06_acceptance import SEEDS


def fixture(root):
    root.mkdir(parents=True,exist_ok=False)
    base=root/'template.gz';benchmark.fixture(base,1000)
    with gzip.open(base,'rt') as f:
        header=json.loads(next(f));rows=[json.loads(line) for line in f]
    catalog={}
    for seed in SEEDS:
        models={}
        changed=[]
        # Independent key sets across lineages, identical membership within one.
        for row in rows:
            r=list(row);r[0]=hashlib.sha256(f'{seed}:{row[0]}'.encode()).digest()[:16].hex();changed.append(r)
        changed.sort(key=lambda r:r[0])
        keyset=hashlib.sha256(b''.join(bytes.fromhex(r[0]) for r in changed)).hexdigest()
        for alias in ('baseline','candidate'):
            folder=root/str(seed)/alias;folder.mkdir(parents=True)
            policy=folder/'policy.gz';cp=hashlib.sha256(f'{seed}-{alias}'.encode()).hexdigest()
            h=dict(header,source_checkpoint_sha256=cp)
            with gzip.open(policy,'wt') as f:
                f.write(json.dumps(h)+'\n')
                for i,row in enumerate(changed):
                    r=list(row)
                    if i<3:r[4]=[1./len(r[4])]*len(r[4])
                    f.write(json.dumps(r)+'\n')
            mass=folder/'mass';mass.mkdir();zero=mass/'zero-keys.bin'
            zero.write_bytes(b''.join(bytes.fromhex(r[0]) for r in changed[:3]))
            receipt=dict(format='nplayer-average-mass-v1',status='passed',strategy='average',last_average_street=3,
                checkpoint_sha256=cp,policy_sha256=io.sha(policy),rows=1000,average_rows=1000,current_rows=0,
                zero_mass_rows=3,positive_mass_rows=997,keyset_sha256=keyset,zero_keys_sha256=io.sha(zero))
            io.write(mass/'receipt.json',receipt)
            source=dict(path=str(policy),sha256=io.sha(policy),checkpoint=str(folder/'nonexistent-readonly-checkpoint'),
                checkpoint_sha256=cp,mass=str(mass),mass_sha256=io.sha(mass/'receipt.json'),strategy='average',scope=3)
            models[alias]=dict(source=source,mass=receipt,binary=None,audit=None)
        catalog[str(seed)]=models
    io.write(root/'catalog.json',catalog)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);a=p.parse_args();fixture(a.root.absolute())
