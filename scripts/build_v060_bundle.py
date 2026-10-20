"""Prepare one exact v0.6.0 seed bundle; never upload or publish a release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from src.policies.v060_bundle import (CARD_TABLES,DOCS,EVIDENCE,MODELS,VERIFIER,VERSION,
    check_header,digest,layout,names,sha,verify_bundle)

SOURCE=Path(__file__).resolve().parents[1]


def checked_source(source):
    if not digest(source,40) or subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()!=source:
        raise ValueError('full checked-out source commit required')
    if subprocess.run(['git','diff','--quiet',source,'--'],cwd=SOURCE).returncode:
        raise ValueError('source tracked bytes must be clean')
    return SOURCE


def build(seed,model,tables,out,source,*,publication_approved=False):
    repo=checked_source(source);pin=MODELS[seed]
    model=Path(model)
    if not model.is_file() or model.stat().st_size!=pin['bytes']:raise ValueError('qualified model length differs')
    for name,p in CARD_TABLES.items():
        f=Path(tables)/name
        if not f.is_file() or f.stat().st_size!=p['bytes'] or sha(f)!=p['sha256']:raise ValueError('wrong K50 table '+name)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    parts=[];whole=hashlib.sha256()
    with model.open('rb') as f:
        prefix=f.read(128)
        if len(prefix)!=128:raise ValueError('short source prefix')
        import struct
        n=struct.unpack_from('<Q',prefix,8)[0]
        if not 0<n<=65536:raise ValueError('source header bound')
        check_header(prefix,f.read(n),seed);f.seek(0)
        for row in layout(seed):
            h=hashlib.sha256();remaining=row['bytes']
            with (out/row['file']).open('xb') as target:
                while remaining:
                    chunk=f.read(min(4*1024**2,remaining))
                    if not chunk:raise ValueError('source ended inside a part')
                    target.write(chunk);h.update(chunk);whole.update(chunk);remaining-=len(chunk)
                target.flush();os.fsync(target.fileno())
            parts.append(dict(row,sha256=h.hexdigest()))
        if f.read(1) or whole.hexdigest()!=pin['sha256']:raise ValueError('source differs from exact qualified binary')
    for name in CARD_TABLES:shutil.copyfile(Path(tables)/name,out/name)
    for name in DOCS:shutil.copyfile(repo/'docs/releases/v0.6.0'/name,out/name)
    shutil.copyfile(repo/'src/policies/v060_bundle.py',out/VERIFIER)
    assets={n:dict(bytes=(out/n).stat().st_size,sha256=sha(out/n)) for n in DOCS+(VERIFIER,)}
    manifest=dict(format='nplayer-v060-release-v1',version=VERSION,seed=seed,source_commit=source,
        publication_approved=publication_approved,evidence=EVIDENCE,model=pin,parts=parts,card_tables=CARD_TABLES,
        table=dict(players=3,stack_bb=100,small_blind=50,big_blind=100,search=False),source_assets=assets)
    name,sums=names(seed);(out/name).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    checks={r['file']:r['sha256'] for r in parts}
    checks.update({n:p['sha256'] for n,p in {**CARD_TABLES,**assets}.items()});checks[name]=sha(out/name)
    (out/sums).write_text(''.join(f'{pin}  {name}\n' for name,pin in sorted(checks.items())))
    return verify_bundle(out,seed,source)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed',choices=MODELS,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--card-tables',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--source-sha',required=True)
    p.add_argument('--publication-approved',action='store_true');a=p.parse_args()
    print(json.dumps(build(a.seed,a.model,a.card_tables,a.out,a.source_sha,publication_approved=a.publication_approved)))


if __name__=='__main__':main()
