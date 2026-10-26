"""Finite M4-only PR444 qualification and one admitted fixed candidate pilot."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.calibrate_six_player_counterfactual_m4 import run_guarded
from scripts.nplayer_four_player_feasibility import sample,sha,write,TABLES
from scripts.nplayer_variable_stack_qualification import source_manifest

SOURCE=Path(__file__).resolve().parents[1]
TARGETS=[5_000_000,25_000_000,100_000_000]
SEED=20261026441011
OLD_COMPLETE='fa275828a1da0d2f3b3b5364437cbfeb3bef01de85815e0ca472f9b7cb9ea411'
OLD_PROVENANCE='20306572b41c607f3c5aad2415770dd6bb6ce09732a885929a930111929e838a'
OLD_ROOT=Path('/Users/dberweger/Local/nplayer-variable-stack-20261026')
EXTRAS=['docs/nplayer-stack-buckets.md','docs/reports/nplayer-variable-stack-feasibility/pilot-provenance.json',
        'docs/reports/nplayer-variable-stack-feasibility/pilot-common-panel.csv',
        'docs/reports/nplayer-variable-stack-feasibility/qualification.json',
        'tests/test_nplayer_stack_buckets.py']

def manifest():
    result=source_manifest(SOURCE)
    result.update({n:sha(SOURCE/n)for n in EXTRAS})
    return result

def references():
    p=SOURCE/EXTRAS[1]
    if sha(p)!=OLD_PROVENANCE:raise ValueError('frozen reference provenance differs')
    pins=json.loads(p.read_text())['file_sha256']
    return [dict(target_nodes=n,checkpoint=str(OLD_ROOT/f'main-v1/native/{n}/checkpoint.gz'),
                 checkpoint_sha256=pins[f'native/{n}/checkpoint.gz'],
                 binary=str(OLD_ROOT/f'main-v1/native/{n}/policy.bin'),binary_sha256=pins[f'native/{n}/policy.bin'])for n in TARGETS]

def validate(c,*,pilot=False):
    if manifest()!=c['source_manifest']:raise ValueError('frozen source differs')
    if sha(sys.executable)!=c['python_sha256']:raise ValueError('qualified Python changed')
    for n in ['thermal','review']:
        if sha(c[n])!=c[n+'_sha256']:raise ValueError(n+' changed')
    review=json.loads(Path(c['review']).read_text())
    if review['study']!='PR444' or not review['resolved']:raise ValueError('review unresolved')
    if sha(OLD_ROOT/'main-v1/COMPLETE.json')!=OLD_COMPLETE or (OLD_ROOT/'main-v1/failure.json').exists():raise ValueError('reference completion changed')
    if c['references']!=references():raise ValueError('reference set differs')
    for spec in c['references']:
        for n in ['checkpoint','binary']:
            if sha(spec[n])!=spec[n+'_sha256']:raise ValueError('reference payload changed')
    for n,pin in TABLES.items():
        if sha(Path(c['tables'])/n)!=pin:raise ValueError('K50 changed')
    if pilot:
        for n in ['binary','qualification','owner_admission']:
            if sha(c[n])!=c[n+'_sha256']:raise ValueError(n+' changed')
        q=json.loads(Path(c['qualification']).read_text())
        original=Path(c['qualification']).parent/'config.json'
        if (q['status']!='passed' or not q['no_pilot_started'] or sha(original)!=q['config_sha256']
                or q['binary_sha256']!=c['binary_sha256'] or q['source_manifest']!=c['source_manifest']):
            raise ValueError('qualification/binary/source binding differs')
        owner=json.loads(Path(c['owner_admission']).read_text())
        acceptance(owner,review,q['pilot_quote'])

def acceptance(owner,review,quote):
    if not review.get('pilot_cleared'):raise ValueError('independent pilot review unresolved')
    if (owner['status']!='owner-approved' or owner['study']!='PR444' or owner['targets']!=TARGETS
            or owner['seed']!=SEED or owner['max_entries']!=10_000_000 or owner['threads']!=2
            or owner['allocation_seconds']!=1200):raise ValueError('fixed owner allocation differs')
    if quote['reserved_seconds']>1200:raise ValueError('measured reserve exceeds accepted allocation')

def reference_barrier(root):
    proof=json.loads((root/'reference/verified.json').read_text())
    if proof['status']!='passed' or not proof['no_training']:raise ValueError('reference audit incomplete')
    rows=list(csv.DictReader((SOURCE/EXTRAS[2]).open()))
    for n in TARGETS:
        actual=json.loads((root/f'reference/{n}/original-panel.json').read_text())['cells']
        expected=[x for x in rows if int(x['target_nodes'])==n]
        if len(expected)!=324:raise ValueError('reference cell inventory differs')
        for x in expected:
            got=actual[int(x['tuple'])][int(x['seat'])][int(x['street'])]
            if got!=[int(x[k])for k in ['missing','zero_mass','positive_mass','observations']]:raise ValueError('original reference support differs')

def panel_barrier(folder):
    values={n:json.loads((folder/(n+'-panel.json')).read_text())for n in ['original','heldout','union']}
    for name,x in values.items():
        if x['protected_contract_violations']!=0 or not x['checkpoint_binary_panel_float64_parity']:
            raise ValueError('panel contract/probability failure:'+name)
    if values['original']['seed']!=20261026441002 or values['heldout']['seed']!=20261026443002:
        raise ValueError('fixed observation seed differs')
    if values['union']['observations']!=values['original']['observations']+values['heldout']['observations']:
        raise ValueError('union panel inventory differs')

def quote(root):
    newer=json.loads((root/'native/verified.json').read_text())
    old=json.loads((root/'legacy-mixture/verified.json').read_text())
    # A tiny fixture ratio is an uncertainty scenario, not mature measured speed.
    scale=max(1.,newer['wall_seconds']/old['wall_seconds'])
    stage=json.loads((root/'stage-costs.json').read_text())
    refcost=next(x['wall_seconds']for x in stage if x['phase']=='reference-audit')
    return dict(central_seconds=141.44622729101684*scale+120,
      reserved_seconds=3*133.95846566697583*scale+2*6.261383291857783+300,
      accepted_allocation_seconds=1200,fixture_ratio=scale,measured_fixture_seconds=newer['wall_seconds'],
      measured_legacy_fixture_seconds=old['wall_seconds'],reference_audit_already_completed_seconds=refcost,
      source='PR441 capped complete pipeline, scaled by max(1,new/old whole tiny fixture ratio); central+120readout; reserve3xnative+2xsixreplays+300proof/readout. Reference audit completed in qualification and reused, not repeated.',
      not_a_mature_speed_measurement=True,no_completion_guarantee=True,new_disk_bytes=8*2**30,disk_headroom_bytes=4*2**30,
      ram_bytes=5*2**30,ram_headroom_bytes=2**30,no_pilot_started=True)

def run(mode,root,c):
    if 'Apple M4'not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):raise ValueError('M4 only')
    if 'AC Power'not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c)
    locks=[];stages=[];clock=time.monotonic()
    try:
        for p in [Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.stack-buckets.lock']:
            f=p.open('a+');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        validate(c,pilot=mode=='pilot');before=sample(root,c['thermal'])
        ram,disk=(5,8)if mode=='pilot'else(5,4)
        write(root/'admission.json',dict(sample=before,mode=mode,forecast_rss_bytes=ram*2**30,ram_headroom_bytes=2**30,
          forecast_new_disk_bytes=disk*2**30,disk_headroom_bytes=4*2**30,no_elapsed_time_stop=True))
        if before['available_ram_bytes']<(ram+1)*2**30 or before['disk_free_bytes']<(disk+4)*2**30 or before['thermal_state']not in ['nominal','fair']:
            raise ValueError('forecast/headroom admission unavailable')
        def stage(name,command):
            if (root/'STOP').exists():raise ValueError('ownerSTOP')
            d=root/'stages'/name;d.mkdir(parents=True,exist_ok=False);write(d/'config.json',c)
            write(root/'status.json',dict(status='running',phase=name,completed_stages=len(stages)))
            stages.append(run_guarded(d,c,phase=name,command=[str(x)for x in command],owner_stop=root/'STOP'))
            write(root/'stage-costs.json',stages)
        exe=SOURCE/'native/hu20-trainer/target/release/examples'
        if mode=='qualify':
            os.environ['CARGO_BUILD_JOBS']='2'
            for name in ['stack_buckets_tests','multi_stacks::tests','multi_key_tests::exact_key_bytes']:
                stage('unit-'+name.replace('::','-'),['cargo','test','--locked','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml','--lib',name])
            stage('all-examples',['cargo','test','--locked','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml','--examples','--no-run'])
            stage('build',['cargo','build','--locked','--release','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml','--example','nplayer_stack_buckets','--example','nplayer_variable_stack','--example','nplayer_train','--example','nplayer_policy'])
            binary_sha=sha(exe/'nplayer_stack_buckets');write(root/'PRE-FIXTURE-BINARY.json',dict(binary_sha256=binary_sha))
            stage('native-fixtures',[exe/'nplayer_stack_buckets','qualify',c['tables'],root/'native'])
            stage('legacy-mixture',[exe/'nplayer_variable_stack','qualify',c['tables'],root/'legacy-mixture'])
            for file,original in [('full.gz','full.gz'),('average.gz','average.gz'),('policy.bin','policy.bin'),('initial.jsonl','initial.jsonl'),('repeat.jsonl','repeat.jsonl')]:
                if sha(root/'legacy-mixture'/file)!=sha(OLD_ROOT/'qualification-v1/native'/original):raise ValueError('legacy mixture bytes changed:'+file)
            for label in ['native','legacy-mixture']:
                for arm in ['initial','repeat']:
                    stage(f'replay-{label}-{arm}',[sys.executable,'-m','scripts.check_nplayer_policy_replay',root/label/(arm+'.jsonl')])
            for schema in ['history','live-order']:
                out=root/f'{schema}.gz';avg=root/f'{schema}-average.gz'
                stage('fixed-'+schema,[exe/'nplayer_train','--players','3','--stack-bb','20','--small-blind','50','--big-blind','100','--seed','20261026441003','--nodes','100000','--last-average-street','3','--max-entries','100000','--freeze-at-cap','--fast','--threads','2','--roots-per-seat','8','--max-seconds','1e100','--card-buckets',c['tables'],'--key-schema',schema,'--out',out])
                stage('fixed-export-'+schema,[exe/'nplayer_policy','export',out,sha(out),'average',avg])
                if sha(out)!=sha(OLD_ROOT/f'qualification-v1/{schema}-new.gz')or sha(avg)!=sha(OLD_ROOT/f'qualification-v1/{schema}-new-average.gz'):raise ValueError('legacy fixed bytes changed')
            rm=dict(out=str(root/'reference'),tables=c['tables'],references=c['references'])
            write(root/'reference-manifest.json',rm)
            stage('reference-audit',[exe/'nplayer_stack_buckets','reference',root/'reference-manifest.json'])
            reference_barrier(root)
            panel_barrier(root/'native')
            for n in TARGETS:panel_barrier(root/'reference'/str(n))
            proof=json.loads((root/'native/verified.json').read_text())
            if proof['status']!='passed' or not proof['no_pilot_started']:raise ValueError('native qualification incomplete')
            validate(c)
            if sha(exe/'nplayer_stack_buckets')!=binary_sha:raise ValueError('qualified executable changed')
            write(root/'COMPLETE.json',dict(status='passed',no_pilot_started=True,source_manifest=c['source_manifest'],config_sha256=sha(root/'config.json'),
              binary_sha256=binary_sha,pilot_quote=quote(root),native_proof_sha256=sha(root/'native/verified.json'),reference_proof_sha256=sha(root/'reference/verified.json'),
              wall_seconds=time.monotonic()-clock,stages=stages))
        else:
            m=dict(mode='pilot',seed=SEED,targets=TARGETS,max_entries=10_000_000,threads=2,tables=c['tables'],owner_admission=c['owner_admission'],out=str(root/'native'))
            write(root/'manifest.json',m);stage('native-pilot',[c['binary'],'pilot',root/'manifest.json'])
            final=json.loads((root/'native/native-complete.json').read_text())
            if final['status']!='native-complete-proof-pending'or[e['target_nodes']for e in final['endpoints']]!=TARGETS or any(e['actual_nodes']<e['target_nodes']for e in final['endpoints']):raise ValueError('native endpoints incomplete')
            for n in TARGETS:
                panel_barrier(root/'native'/str(n))
                for arm in ['initial','repeat']:stage(f'replay-{n}-{arm}',[sys.executable,'-m','scripts.check_nplayer_policy_replay',root/f'native/{n}/{arm}.jsonl'])
                if sha(root/f'native/{n}/initial.jsonl')!=sha(root/f'native/{n}/repeat.jsonl'):raise ValueError('reproduction differs')
            validate(c,pilot=True)
            write(root/'COMPLETE.json',dict(status='passed',no_extra_training=True,no_strength_claim=True,
              native_readout_sha256=sha(root/'native/native-complete.json'),qualification_sha256=c['qualification_sha256'],config_sha256=sha(root/'config.json'),
              source_manifest_sha256=hashlib.sha256(json.dumps(c['source_manifest'],sort_keys=True).encode()).hexdigest(),wall_seconds=time.monotonic()-clock,stages=stages))
        write(root/'status.json',dict(status='complete',mode=mode,no_strength_claim=True))
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),terminal=True,no_retry=True));raise
    finally:
        write(root/'WRAPPER-COST.json',dict(wall_seconds=time.monotonic()-clock,scope='Includes stages; no elapsed-time cutoff'))
        for f in reversed(locks):f.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['qualify','pilot']);p.add_argument('root',type=Path);p.add_argument('config',type=Path)
    a=p.parse_args();run(a.mode,a.root,json.loads(a.config.read_text()))
if __name__=='__main__':main()
