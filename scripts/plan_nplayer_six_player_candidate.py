"""Reproducible six-player four-endpoint scenarios from verified PR415 metadata."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]
INPUT='docs/reports/nplayer-five-player-candidate/results.json'


def proposal():
    path=SOURCE/INPUT;x=json.loads(path.read_text());c=x['costs']['categories'];e=x['results']['endpoints'];a=e['baseline'];b=e['candidate']
    components=[]
    def add(name,value,reserve=2):components.append(dict(name=name,central_seconds=value,reserved_seconds=value*reserve))
    active=a['active_training_seconds']+b['active_training_seconds']*12e9/(b['counts']['nodes']-a['counts']['nodes'])
    add('active traversal0→15B',active*1.25)
    add('four checkpoint saves',2*(a['save_seconds']+b['save_seconds'])*1.25)
    add('four train startup/resume/hash residuals',((a['stage_wall_seconds']-a['elapsed_seconds'])+3*(b['stage_wall_seconds']-b['elapsed_seconds']))*1.25)
    for kind in ('export','source audit','conversion','binary audit'):add('four endpoints '+kind,c[kind]['wall_seconds']*2*1.25)
    add('three anchored arena jobs initial+repeat',c['arena']['wall_seconds']*3*1.25)
    add('initial independent replay including duplicate3B',c['independent replay']['wall_seconds']*3*1.2*1.25)
    add('five paired verification/readouts',c['pair readout']['wall_seconds']*5*1.2*1.25)
    add('global complete proof/tail readout',c['global readout']['wall_seconds']*5*1.2*1.25)
    add('between-stage validation',x['costs']['between_stage_and_validation_seconds']*3*1.25)
    add('exact source build+qualification',600)
    add('saved PR415 trace diagnosis',600)
    add('report publication',900,5/3)
    return dict(status='owner-authorized-source-qualification-pending',input=INPUT,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        players=6,stack_bb=100,seed=2026102361001,targets=[3_000_000_000,6_000_000_000,10_000_000_000,15_000_000_000],
        contrasts=[['3b','6b'],['6b','10b'],['10b','15b'],['3b','10b'],['3b','15b']],fields=8,blocks_per_field=4096,seatings=12,
        unique_initial_instances=8*4096*12*4,physical_initial_instances=8*4096*12*2*3,
        reproduction_instances=8*4096*12*2*3,statistical_family='40 one-sided95 Student-t/Bonferroni; trained lower>0; seven scripted/mixed lower>-5',
        components=components,central_seconds=sum(r['central_seconds'] for r in components),reserved_seconds=sum(r['reserved_seconds'] for r in components),accepted_planning_seconds=43200,
        storage=dict(model_artifacts_bytes=160*2**30,traces_bytes=40*2**30,source_qualification_logs_bytes=10*2**30,working_headroom_bytes=30*2**30,provisional_free_bytes=240*2**30,owner_start_during_cleanup=True,no_automatic_disk_stop=True),
        assumptions='PR415 five-player measurements,25percent six-player scenario penalty,12vs10seatings only for hand-dependent work; existing two-model runner three anchored jobs; duplicate3B is not extra sample. Reserve not guarantee or time kill.',
        excludes=['archival/upload','release packaging','new training seeds','capacity/menu/search changes','automatic outcome extension'],
        launch_requires=['exact source qualification','completed saved-trace diagnosis','manual live disk/RAM/mutex admission','immutable owner start-during-space-arrangement receipt'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(proposal(),f,indent=2);f.write('\n')


if __name__=='__main__':main()
