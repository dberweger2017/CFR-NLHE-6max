"""One-use small engineering qualification; no mature arena or training mode."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from scripts import nplayer_four_player_feasibility as tools
from scripts import nplayer_paired_evidence as evidence
from scripts import nplayer_composition_evidence as composition

SOURCE=Path(__file__).resolve().parents[1]
FIELDS=[('trained',['peer']*5),('random',['bot=random']*5),('check-call',['bot=check-call']*5),('tight-aggressive',['bot=tight-aggressive']*5),('pot-pressure',['bot=pot-pressure']*5),('call-pressure',['bot=check-call']*3+['bot=pot-pressure']*2),('random-tight',['bot=random']+['bot=tight-aggressive']*4),('trained-call-pressure',['peer']+['bot=check-call']*2+['bot=pot-pressure']*2)]
SCHEDULE=[[(s+r)%6 for s in range(6)] for r in range(6)]+[[(r-s)%6 for s in range(6)] for r in range(6)]


def manifest(root,catalog,tables,phase,*,threads=4,focals=None,diagnostics=True,one=False):
    directory=root/phase;directory.mkdir(exist_ok=False);cases=[]
    for i,(name,opponents) in enumerate(FIELDS[:1] if one else FIELDS):
        cases.append(dict(name=name,players=6,stack_bb=100,blocks=2,root=20261024759901+i,schedule=SCHEDULE,focals=focals or ['control','augmented'],opponents=opponents,traces=[str(directory/(name+'-'+a+'.jsonl')) for a in ['a','b']],summary=str(directory/(name+'-cost.json')),composition_diagnostics=diagnostics))
    return dict(format='nplayer-paired-manifest-v1',threads=threads,tables=tables,models=dict(catalog,augmented=dict(composition=composition.FORMAT,base='control',donor='donor'),identity_composition=dict(composition=composition.FORMAT,base='control',donor='control')),cases=cases)


def qualify(a):
    root=a.root.absolute()
    if root.exists():raise FileExistsError('qualification attempt exists; preserve, no automatic retry')
    root.mkdir(parents=True);tick=time.monotonic();source=json.loads(a.source_manifest.read_text())
    for name,digest in source['files'].items():
        if tools.sha(SOURCE/name)!=digest:raise ValueError('qualified source pin changed')
    catalog=json.loads(a.catalog.read_text());rows={k:composition.pinned_rows(catalog[k]) for k in ['control','donor']}
    for spec in catalog.values():
        if tools.sha(spec['path'])!=spec['sha256']:raise ValueError('small binary fixture changed')
    normal=Path.home()/'Local/.hu20-m4-research.lock' if sys.platform=='darwin' else Path('/tmp/cfr-cygnus-exclusive.lock')
    locks=[open(normal,'a+'),open('/tmp/cfr-nplayer-composition.lock','a+')]
    for lock in locks:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    env=dict(os.environ,NPLAYER_STOP_FILE=str(root/'STOP'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CARGO_TARGET_DIR=str(root/'build'))
    config=dict(source=source,catalog=catalog,tables=str(a.tables),thermal=str(a.thermal),legacy=str(a.legacy),legacy_sha256=tools.sha(a.legacy),source_manifest_sha256=tools.sha(a.source_manifest),catalog_sha256=tools.sha(a.catalog),python=sys.executable,python_sha256=tools.sha(sys.executable),no_training_or_exports=True)
    tools.write(root/'config.json',config);os.chmod(root/'config.json',0o444)
    if sys.platform=='darwin':
        if a.thermal is None:raise ValueError('M4 thermal reader required')
        sup=tools.Supervisor(root,env,a.thermal)
    elif sys.platform=='linux':
        from scripts import nplayer_bb200_feasibility as linux
        sup=linux.Supervisor(root,env)
    else:raise ValueError('qualified M4 or bb128 platform required')
    tools.write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time()))
    cargo=Path.home()/'.cargo/bin/cargo';args=['--release','--locked','--offline','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml']
    try:
        sup.stage('native-tests',[cargo,'test',*args,'--lib','--example','nplayer_paired_arena'])
        sup.stage('native-build',[cargo,'build',*args,'--example','nplayer_paired_arena'])
        sup.stage('python-tests',[sys.executable,'-m','unittest','tests.test_nplayer_composition','tests.test_nplayer_paired_evidence','tests.test_nplayer_shared_observations','-q'])
        binary=root/'build/release/examples/nplayer_paired_arena'
        def arena(phase,legacy=False,**kw):
            m=manifest(root,catalog,str(a.tables),phase,**kw);path=root/(phase+'-manifest.json');tools.write(path,m);sup.stage('arena-'+phase,[a.legacy if legacy else binary,'batch',path]);return m
        initial=arena('initial');repeat=arena('repeat');serial=arena('serial',threads=1);off=arena('diagnostics-off',diagnostics=False)
        proofs={};audits={};structural={}
        for left,right,single,disabled in zip(initial['cases'],repeat['cases'],serial['cases'],off['cases']):
            for arm in range(2):
                first=left['traces'][arm]
                if tools.sha(first)!=tools.sha(right['traces'][arm]) or tools.sha(first)!=tools.sha(single['traces'][arm]):raise ValueError('reproduction/thread parity differs')
                composition.payload_parity(first,disabled['traces'][arm],strip_composition=True)
                name='replay-'+left['name']+'-'+str(arm);sup.stage(name,[sys.executable,'-m','scripts.nplayer_paired_evidence','replay',first])
            proof=[root/'measurements'/('replay-'+left['name']+'-'+str(i))/'stdout.log' for i in range(2)]
            pair=evidence.verified_pair(*left['traces'],*right['traces'],*proof)
            if pair['blocks']!=2 or pair['schedule']!=SCHEDULE:raise ValueError('small paired scope differs')
            proofs[left['name']]=dict(blocks=pair['blocks'],hands_per_arm=pair['hands_per_arm'],trace_sha256=[tools.sha(t) for t in left['traces']])
            audits[left['name']]=composition.audit(left['traces'][1],rows['control'],rows['donor'],catalog)
            structural[left['name']]=composition.structural(left['traces'][1])
        identity=arena('identity',focals=['control','identity_composition'],one=True)['cases'][0]
        composition.payload_parity(*identity['traces'],strip_composition=True)
        self_a=arena('self',focals=['augmented','augmented'],one=True)['cases'][0]
        self_b=arena('self-repeat',focals=['augmented','augmented'],one=True)['cases'][0]
        if len({tools.sha(t) for t in self_a['traces']+self_b['traces']})!=1:raise ValueError('composition self not byte-identical')
        plain=arena('plain',focals=['control','donor'],one=True)['cases'][0]
        old=arena('legacy',legacy=True,focals=['control','donor'],one=True)['cases'][0]
        if any(tools.sha(l)!=tools.sha(r) for l,r in zip(plain['traces'],old['traces'])):raise ValueError('ordinary pre-composition arena changed')
        # Corrupt a copied derived tag, never a protected source. It must fail
        # the independent oracle before this package can qualify.
        bad=root/'bad-selection.jsonl';lines=Path(initial['cases'][0]['traces'][1]).read_text().splitlines();changed=False
        for i,line in enumerate(lines[1:],1):
            value=json.loads(line)
            for lookup in value['lookups']:
                if 'composition' in lookup:
                    lookup['composition']['source']='wrong';lines[i]=json.dumps(value);changed=True;break
            if changed:break
        if not changed:raise ValueError('qualification had no composed decisions')
        bad.write_text('\n'.join(lines)+'\n')
        try:composition.audit(bad,rows['control'],rows['donor'],catalog)
        except ValueError:pass
        else:raise ValueError('corrupt selection accepted')
        if any(s['returncode']!=0 for s in sup.costs):raise ValueError('stage failure')
        for name,digest in source['files'].items():
            if tools.sha(SOURCE/name)!=digest:raise ValueError('source changed during qualification')
        result=dict(status='qualified-engineering',source=source,config_sha256=tools.sha(root/'config.json'),binary_sha256=tools.sha(binary),legacy_sha256=config['legacy_sha256'],initial_hands=384,reproduction_hands=384,all_initial_replayed=True,proofs=proofs,selection_audits=audits,structural=structural,all_nine_selector_combinations=True,exact_original_zero_mass_precedence=True,identity_composition_rng_parity=True,composition_self_exact_zero=True,diagnostics_rng_parity=True,serial_parallel_parity=True,old_ordinary_arena_byte_parity=True,corrupted_selection_refused=True,stages=len(sup.costs),complete_wall_seconds=time.monotonic()-tick,no_strength_claim=True,no_main_started=True)
        tools.write(root/'results.json',result);tools.write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=tools.sha(root/'results.json')))
    except BaseException as e:
        tools.write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));tools.write(root/'status.json',dict(status='failed'));raise
    finally:
        for lock in locks:lock.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ['root','catalog','tables','legacy','source-manifest']:p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--thermal',type=Path)
    qualify(p.parse_args())


if __name__=='__main__':main()
