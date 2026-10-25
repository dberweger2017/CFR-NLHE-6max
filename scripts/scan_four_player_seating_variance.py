"""Read-only PR413 saved-data sizing. No arena, model load or new hands."""
from pathlib import Path
import hashlib
import json
import math
import os
import statistics
import time
import resource

ROOT=Path('/home/dberweger/nplayer-four-player-candidate-20261023/main-v1/arena-initial')
FIELDS=['trained','random','check-call','tight-aggressive','pot-pressure','call-pressure','random-tight','trained-call-pressure']
SCHEDULE=[[(s+r)%4 for s in range(4)] for r in range(4)]+[[(-s+r)%4 for s in range(4)] for r in range(4)]
assert len({tuple(x) for x in SCHEDULE})==8
def main():
    expected=json.loads((Path(__file__).resolve().parents[1]/'docs/reports/nplayer-four-player-candidate/results.json').read_text())['arena_costs']['initial']
    os.nice(19)
    def summary(v):
        return {'blocks':len(v),'mean_bb100':statistics.mean(v),'sd_bb100':statistics.stdev(v),
                'se_bb100':statistics.stdev(v)/math.sqrt(len(v))}
    out={'kind':'saved-data variance sizing only','schedule':SCHEDULE,'fields':{},'files':{},'started_epoch':time.time()}
    for field in FIELDS:
        arms=[]
        for arm in ['a','b']:
            p=ROOT/(field+'-'+arm+'.jsonl');before=p.stat();sha=hashlib.sha256();values=[];selected_bytes=0;all_bytes=0;full=[]
            with p.open('rb') as f:
                line=next(f);sha.update(line);header=json.loads(line)
                expected_ids={tuple(ids):i for i,ids in enumerate(header['schedule'])}
                indices={expected_ids[tuple(ids)] for ids in SCHEDULE}
                running=[];running_all=[];current=0;rows=0
                for line in f:
                    sha.update(line);row=json.loads(line);b=row['block'];perm=row['permutation'];rows+=1;all_bytes+=len(line)
                    assert b==current and tuple(row['identities'])==tuple(header['schedule'][perm])
                    x=row['rewards'][row['identities'].index(0)]*100/row['bb']
                    running_all.append(x)
                    if perm in indices:running.append(x);selected_bytes+=len(line)
                    if perm==23:
                        assert len(running)==8 and len(running_all)==24
                        values.append(statistics.mean(running));full.append(statistics.mean(running_all));running=[];running_all=[];current+=1
            after=p.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
            assert len(values)==4096 and rows==98304 and not running
            assert sha.hexdigest()==expected[field]['trace_sha256'][0 if arm=='a' else 1], 'source SHA differs'
            arms.append((values,full));out['files'][p.name]={'sha256':sha.hexdigest(),'bytes':before.st_size,'selected_hand_bytes':selected_bytes,'all_hand_bytes':all_bytes}
        a,b=arms
        out['fields'][field]={'absolute_3b_8':summary(a[0]),'absolute_10b_8':summary(b[0]),
                              'paired_10b_minus_3b_8':summary([y-x for x,y in zip(a[0],b[0])]),
                              'absolute_3b_24':summary(a[1]),'absolute_10b_24':summary(b[1]),
                              'paired_10b_minus_3b_24':summary([y-x for x,y in zip(a[1],b[1])])}
        print(json.dumps({'progress_field':field}),file=__import__('sys').stderr,flush=True)
    out['wall_seconds']=time.time()-out['started_epoch'];ru=resource.getrusage(resource.RUSAGE_SELF)
    out['cost']={'user_cpu_seconds':ru.ru_utime,'system_cpu_seconds':ru.ru_stime,'max_rss_kib':ru.ru_maxrss}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
