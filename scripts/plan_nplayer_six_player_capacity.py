"""Provisional capacity scenarios from PR417 metadata, never a launch admission."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import NormalDist

SOURCE=Path(__file__).resolve().parents[1]
INPUT='docs/reports/nplayer-six-player-candidate/costs.json'
RESULTS='docs/reports/nplayer-six-player-candidate/results.json'


def proposal():
    path=SOURCE/INPUT;c=json.loads(path.read_text());r=json.loads((SOURCE/RESULTS).read_text());t=c['training'];categories=c['categories'];components=[]
    def add(name,seconds):components.append(dict(name=name,central_seconds=seconds,reserved_seconds=2*seconds))
    add('fresh0to10B active traversal;1.5x observed seconds',sum(z['active_training_seconds'] for z in t[:3])*1.5)
    add('one500M checkpoint save;2x10B250M save',t[2]['save_seconds']*2)
    add('fresh startup/hash residual;2x priorfresh',t[0]['startup_resume_hash_other_seconds']*2)
    tools=sum(categories[k]['wall_seconds']/4 for k in ['export','source audit','binary conversion','binary audit']);add('one500M endpoint export/audit/convert/binaryaudit;2x perendpoint',tools*2)
    add('three-model arena plus peer reload initial+repeat;2.5x prior job',sum(z['stage_wall_seconds'] for z in c['arena'] if z['checkpoint']=='10b')*2.5)
    add('initial independent replay;1.25x onejob',categories['independent replay']['wall_seconds']/3*1.25)
    add('eight paired summaries;1.25x onecontrast',categories['paired summaries']['wall_seconds']/5*1.25)
    add('global proof/readout conservative wholepriorallowance',categories['global readout']['wall_seconds'])
    add('inline shared-query evidence/readout allowance; unmeasured',900)
    add('fresh build/source qualification allowance',900)
    add('compact reporting allowance',900)
    family_critical=NormalDist().inv_cdf(1-.05/8)
    power=[]
    for gate in r['gates']:
        if gate['contrast']!='3b-10b':continue
        se=gate['standard_error_bb100'];margin=0 if gate['field']=='trained' else -5
        power.append(dict(field=gate['field'],reference_se_bb100=se,margin_bb100=margin,
            normal_reference_power=[dict(true_delta_bb100=delta,pass_probability=NormalDist().cdf((delta-margin)/se-family_critical)) for delta in ([0,25,50,75] if margin==0 else [0,10,25])]))
    return dict(status='provisional-not-admitted',basis=INPUT,basis_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        basis_raw_result_sha256=r['source_result_sha256'],players=6,stack_bb=100,seed=2026102361001,capacity=500000000,control_capacity=250000000,target=10000000000,
        components=components,central_seconds=sum(x['central_seconds'] for x in components),reserved_seconds=sum(x['reserved_seconds'] for x in components),proposed_planning_seconds=25200,accepted_planning_seconds=None,
        arena_resident_models=3,linear_training_peak_gib=2*categories['training including save/startup']['sampled_peak_rss_bytes']/2**30,
        linear_arena_peak_gib=2*categories['arena initial+reproduction']['sampled_peak_rss_bytes']/2**30,memory_planning_allowance_gib=75,no_automatic_memory_stop=True,
        storage=dict(new_model_artifacts_gib=2*sum(c['artifact_sizes']['models']['10b'].values())/2**30,new_artifact_evidence_aux_allowance_gib=95,working_allowance_gib=25,new_free_scenario_gib=120,headroom_included=True,no_live_floor_or_automatic_disk_stop=True),
        blocks_per_field=4096,seatings=12,fields=8,initial_hand_instances=786432,reproduction_hand_instances=786432,
        statistics='one family8 one-sided95Studentt/Bonferroni,trainedlower>0,script/mixedlower>-5,df4095; powerbelow normalapproximations using older3Bto10BSE, NOT measuredcapacityvariance',
        reference_power=power,assumptions=['1.5xtraversalseconds/2xrowwork and storage are scenarios, keymix/freeze/compression maydiffer.','Three resident tables:250Mcontrol+500Mcandidate+250Mpeer. Prior runtime included sharedhostcleanup.','Inline diagnostics and larger capacity require exactsource smallqualification and calibrated cost before main; quote mayneed revision.'],
        launch_requires=['owner accepted complete quote','exact source and diagnostic parity qualification','protected control+peer pins','manual fresh actual storage/RAM/thermal/normalmutex review'],
        no_training_or_main_started=True,no_automatic_extension=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(proposal(),f,indent=2);f.write('\n')


if __name__=='__main__':main()
