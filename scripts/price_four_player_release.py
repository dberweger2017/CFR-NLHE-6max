"""Planning arithmetic only. Run with the existing SciPy runtime; no model loads."""
import json
import math
import scipy
from scipy.stats import t, nct

def main(data):
    f=data['seating']['fields']; historical=data['historical']; banks=16;family=27;alpha=.05/family;scale=1.5
    crit_bank=float(t.ppf(1-alpha,banks-1))
    effects={'random':100,'check-call':50,'tight-aggressive':10,'pot-pressure':10,
             'call-pressure':50,'random-tight':25,'trained-call-pressure':25}
    def chances(sd,n,gap,k=1.):
        ncp=gap*math.sqrt(n)/(sd*k)
        bank=float(nct.sf(crit_bank,banks-1,ncp))
        pooled=float(nct.sf(float(t.ppf(1-alpha,n-1)),n-1,ncp))
        return dict(bank_rule=bank,pooled_rule=pooled,both_lower_bound=max(0,bank+pooled-1),
                    both_upper_bound=min(bank,pooled))
    def size(sd,gap):
        n=16384
        while chances(sd,n,gap,scale)['both_lower_bound']<.8:n+=16384
        return n
    rows=[]
    for field,effect in effects.items():
        sd=f[field]['absolute_10b_24' if field in ('call-pressure','random-tight','trained-call-pressure') else 'absolute_10b_8']['sd_bb100'];n=size(sd,effect)
        rows.append(dict(gate=field,metric='absolute',sd=sd,sd_source='measured PR413 24-seating SD for mixed fields, eight-seating SD for homogeneous fields',
                         effect=effect,margin=0,blocks=n,blocks_per_bank=n//banks,
                         scenarios={str(k):chances(sd,n,effect,k) for k in [1,1.5,2]}))
    sd=f['trained']['paired_10b_minus_3b_8']['sd_bb100']
    for gate,effect,margin in [('own-reciprocal',25,0),('cyclic-fixed-peer',0,-5)]:
        n=size(sd,effect-margin)
        rows.append(dict(gate=gate,metric='paired',sd=sd,
                         sd_source='PR413 eight-seating one-sided field paired SD, unmeasured proxy for this new estimand; no reciprocal-halving variance discount',
                         effect=effect,margin=margin,blocks=n,blocks_per_bank=n//banks,
                         scenarios={str(k):chances(sd,n,effect-margin,k) for k in [1,1.5,2]}))
    stages=historical['costs']['stages'];cats=historical['costs']['categories'];arena=historical['arena_costs']
    by={x['gate']:x for x in rows}
    plays={field:sum(arena[p][field]['play_seconds'] for p in ['initial','repeat']) for field in f}
    replay={field:sum(s['wall_seconds'] for s in stages if s['phase'] in ('replay-'+field+'-0','replay-'+field+'-1')) for field in f}
    pair={field:next(s['wall_seconds'] for s in stages if s['phase']=='pair-'+field) for field in f}
    files=data['seating']['files']
    physical=0;raw=0;replay_seconds=0;play_seconds=0;pair_seconds=0
    evidence=[]
    for field,r in by.items():
        peer=field in ('own-reciprocal','cyclic-fixed-peer');old='trained' if peer else field
        seatings=24 if field in ('call-pressure','random-tight','trained-call-pressure') else 8
        arms=2 if peer else 1;n=r['blocks'];mult=3*n/4096
        physical+=3*n*seatings*arms
        source_bytes=sum(files[old+'-'+a+'.jsonl']['all_hand_bytes' if seatings==24 else 'selected_hand_bytes'] for a in (['a','b'] if peer else ['b']))
        raw+=source_bytes*mult
        # Original timings cover 24 seatings and two arms; reproduction still does all compute.
        play_seconds+=plays[old]*mult*(seatings/24)*(1 if peer else .5)
        replay_seconds+=replay[old]*mult*(seatings/24)*(1 if peer else .5)
        pair_seconds+=pair[old]*mult*(seatings/24)*(1 if peer else .5)
        evidence.append(dict(gate=field,lineages=3,blocks_each=n,physical_arms=arms,seatings=seatings,initial_hands=3*n*seatings*arms,
                             predicted_initial_trace_bytes=source_bytes*mult))
    active=sum(historical['results']['endpoints'][x]['active_training_seconds'] for x in ['baseline','candidate'])
    saves=sum(historical['results']['endpoints'][x]['save_seconds'] for x in ['baseline','candidate'])
    other=cats['training']['wall_seconds']-active-saves
    components=[('active training, two independent seeds',2*active,3*active),
                ('four checkpoint saves',2*saves,4*saves),
                ('training loads/hashes and other',2*other,4*other)]
    components += [(name,2*cats[name]['wall_seconds'],4*cats[name]['wall_seconds']) for name in ['export','source audit','conversion','binary audit']]
    # Three loaded policies per lineage group, two complete processes =18 loads.
    components += [('arena model loading, initial plus reproduction',18*120,18*240),
                   ('arena K50/setup and supervisor residual',3*(cats['arena']['wall_seconds']-sum(x['load_seconds']+x['play_seconds'] for p in arena.values() for x in p.values())),6*(cats['arena']['wall_seconds']-sum(x['load_seconds']+x['play_seconds'] for p in arena.values() for x in p.values()))),
                   ('all arena traversal, including hash-only reproduction',play_seconds*1.5,play_seconds*3),
                   ('independent replay of every initial hand',replay_seconds,replay_seconds*2),
                   ('paired/absolute summaries',pair_seconds,pair_seconds*2),
                   ('block digest and reproduction verification allowance',300,900),
                   ('fixed bank/pooled readout',cats['global readout']['wall_seconds']*physical/1572864,cats['global readout']['wall_seconds']*physical/1572864*2),
                   ('source/input/target-host qualification allowance',1800,3600),
                   ('analysis/reporting',900,1800)]
    model_bytes=2*sum([9571488068,10714176426,5636890547,6211700049,2*14197512080])
    # Initial only: repeated bytes are hashed and compared, not saved then deleted.
    digest_bytes=sum(3*r['blocks']*(2 if r['gate'] in ('own-reciprocal','cyclic-fixed-peer') else 1)*48 for r in rows)
    proof_and_source=6*2**30
    nominal=model_bytes+raw+digest_bytes+proof_and_source
    # 1.5x trace reserve protects longer new-seed/new-field trajectories; old models not duplicated.
    reserved=model_bytes*1.1+raw*1.5+digest_bytes*1.5+proof_and_source+20*2**30
    largest_bank=max(x['predicted_initial_trace_bytes']/3/banks for x in evidence)
    # Optional bank-at-a-time staging would need actual cleaner/HDD space and acceptance first.
    nvme_staged=model_bytes*1.1+largest_bank*1.5+proof_and_source+20*2**30
    hdd_staged=raw*1.5+digest_bytes*1.5
    result=dict(
        status='revised planning scenario, not a launched or accepted allocation',scipy_version=scipy.__version__,
        banks=banks,family=family,bank_df=banks-1,bank_critical=crit_bank,
        uncertainty_rule='all 27 gates require BOTH fixed pooled-block Student-t and 16-bank-mean Student-t lower bounds above the same threshold; report the smaller lower bound. No post-outcome interval switch.',
        sizing='80% lower bound on per-gate probability that BOTH rules pass, conditional on listed effects and 1.5x measured four-player field-specific seating SD; exact noncentral-t scenarios. No joint or training-seed power guarantee.',
        rows=rows,evidence=evidence,initial_hands=physical,hash_only_reproduction_hands=physical,
        components=[dict(component=k,central_seconds=c,reserve_seconds=r) for k,c,r in components],
        central_hours=sum(x[1] for x in components)/3600,reserve_hours=sum(x[2] for x in components)/3600,
        model_checkpoint_export_gib=model_bytes/2**30,initial_trace_gib=raw/2**30,digest_gib=digest_bytes/2**30,
        nominal_new_retained_gib=nominal/2**30,required_new_nvme_gib=reserved/2**30,
        hash_only_reproduction_storage='no second complete raw trace tree; retain expected/observed stream and block digests, byte counts, source/model pins and independent initial replay. On first mismatch preserve that full block and stop.',
        staging_option=dict(status='NOT admitted or assumed; requires owner/cleaner confirmation and real free space',
                            new_nvme_peak_gib=nvme_staged/2**30,new_hdd_peak_gib=hdd_staged/2**30,
                            condition='all new model derivatives stay NVMe; verified stable initial banks staged to HDD with readable original paths; all originals/evidence retained; no deletion assumed'),
        storage_caveats=['all existing inputs excluded from new-output totals but protected',
                         '20GiB working headroom included; no future cleanup or compression credit',
                         'whole-job sum of retained new files bounds all-NVMe peak; 1.5x trace reserve not a completion guarantee',
                         'later cleaner ZIP creation needs separate HDD scratch; archive packaging/upload not included',
                         'single-focal generation and hash-sink implementation require tiny parity qualification; no traversal speedup claimed from writing fewer copies'],
        acceptance_margin_note='cyclic margin restored to -5 BB/100 as owner requested; no silent relaxation',
    )
    staging_seconds=raw/2**20/80 + raw/2**20/64
    result['staging_option']['additional_copy_readback_seconds']={'central':staging_seconds,'reserve':2*staging_seconds}
    result['staging_option']['complete_central_hours']=(sum(x[1] for x in components)+staging_seconds)/3600
    result['staging_option']['complete_reserve_hours']=(sum(x[2] for x in components)+2*staging_seconds)/3600
    result['staging_option']['io_assumption']='80MiB/s copy plus 64MiB/s independent readback, one stream; provisional, not an observed staging rate or an admitted allocation'
    return result


if __name__ == "__main__":
    from pathlib import Path
    data=json.loads((Path(__file__).resolve().parents[1]/"docs/reports/four-player-next-allocation/pricing-inputs.json").read_text())
    print(json.dumps(main(data),indent=2,allow_nan=False))
