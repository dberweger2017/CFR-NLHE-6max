"""Fixed complete-decision engineering pilot. Never plays an arena hand."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import resource
from time import monotonic

from scripts.live_river_fixtures import fixture
from src.blueprint.live_river import BINARY, LiveRiver, observation_request
from src.blueprint.native_river import NativeRiver
from src.policies.v060_bundle import MODELS


def run(out, model, k50, binary, prepared):
    out.mkdir(parents=True,exist_ok=False)
    seed='2026101935003'
    views=[fixture(i) for i in range(6)]
    requests=[observation_request(v,16) for v in views]
    result=dict(status='running',seed=seed,model_sha256=MODELS[seed]['sha256'],
                shared_host=True,scope='six synthetic public roots; first four deeper roots, last two near-all-in support controls',
                binary_sha256=sha256(binary.read_bytes()).hexdigest(),
                fixture_request_sha256=sha256(json.dumps(requests,sort_keys=True).encode()).hexdigest(),
                source_files={p:sha256(Path(p).read_bytes()).hexdigest() for p in
                    ['native/hu20-trainer/src/river.rs','native/hu20-trainer/src/river/live.rs',
                     'native/hu20-trainer/src/river/prepared.rs','native/hu20-trainer/examples/river_live.rs',
                     'src/blueprint/live_river.py','scripts/live_river_fixtures.py','scripts/benchmark_live_river.py']},
                cases=[],arena_launched=False)
    def save():
        (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save();tick=monotonic()
    try:
        with LiveRiver(k50,model,MODELS[seed]['sha256'],binary=binary) as worker, NativeRiver(prepared) as control:
            result['loading']=worker.load;save()
            for i,view in enumerate(views):
                row=dict(case=i,board=list(view.board),seat=view.seat,pot_bb=view.pot/view.big_blind,
                         stack_bb=[p.stack/view.big_blind for p in view.players],records=[])
                result['cases'].append(row)
                for sweeps in (16,64,256):
                    measurements=[worker.decide(view,sweeps) for _ in range(3)]
                    if any(x['status']!=measurements[0]['status'] for x in measurements):
                        raise AssertionError('support result is not deterministic')
                    if measurements[0]['status']!='ok':
                        row.update(status='unsupported',reason=measurements[0]['reason'],
                                   decision_seconds=[x['complete_decision_seconds'] for x in measurements])
                        break
                    first=measurements[0]['result']
                    for x in measurements[1:]:
                        for field in ('probabilities','quality','law','coverage','nodes'):
                            if x['result'][field]!=first[field]:raise AssertionError('fixed decision differs: '+field)
                    row.update(status='supported',nodes=first['nodes'],law=first['law'],coverage=first['coverage'])
                    row['records'].append(dict(sweeps=sweeps,quality=first['quality'],probabilities=first['probabilities'],
                                               complete_decision_seconds=[x['complete_decision_seconds'] for x in measurements],
                                               native_timings=[x['result']['timings'] for x in measurements]))
                    save()
                if row.get('status')=='supported':
                    debug=worker.decide(view,1024,debug=True)
                    if debug['status']!='ok':raise AssertionError('high-work reference became unsupported')
                    r=debug['result'];game=r['prepared_game']
                    # Independently recompute values/BR for exactly the supplied
                    # strategy using the scalar native review kernel.
                    fixed={str(n):p for n,p in enumerate(r['average']) if p}
                    cross=control.solve(dict(format='river-prepared-v1',game=game,sweeps=1,fixed=fixed,
                                             scalar_control=True,include_profiles=False))
                    for field in ('exploitability_bb','zero_sum_error_bb'):
                        if abs(cross['quality'][field]-r['quality'][field])>1e-9:
                            raise AssertionError('scalar same-profile quality differs')
                    row['reference_1024']=dict(quality=r['quality'],complete_decision_seconds=debug['complete_decision_seconds'],
                                               scalar_quality=cross['quality'])
                    row['quality_gap_vs_1024']=[x['quality']['exploitability_bb']-r['quality']['exploitability_bb'] for x in row['records']]
                save()
        result['status']='complete'
    except BaseException as error:
        result['status']='failed';result['failure']=repr(error);raise
    finally:
        result['total_wall_seconds']=monotonic()-tick
        result['child_high_water_rss_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024
        result['supported_roots']=sum(c.get('status')=='supported' for c in result['cases'])
        save()
    print(json.dumps({k:result[k] for k in ('status','supported_roots','total_wall_seconds','child_high_water_rss_bytes')}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--k50',type=Path,required=True)
    p.add_argument('--binary',type=Path,default=BINARY);p.add_argument('--prepared',type=Path,required=True)
    a=p.parse_args();run(a.out,a.model,a.k50,a.binary,a.prepared)


if __name__=='__main__':main()
