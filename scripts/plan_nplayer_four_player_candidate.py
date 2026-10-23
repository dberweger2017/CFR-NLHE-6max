"""Cost scenarios from retained PR404 metadata; no host or model access."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

SOURCE=Path(__file__).resolve().parents[1]
INPUT='docs/reports/nplayer-bb200-model-campaign/results.json'


def proposal():
    path=SOURCE/INPUT;r=json.loads(path.read_text());cp=r['training_endpoints'];st=list(r['costs'].values())
    rates=[]
    for name,row in cp.items():
        parent=cp[name.replace('candidate','baseline')]['counts']['nodes'] if name.startswith('candidate-') else (1000008098 if name.endswith('2026102240001') else 0)
        rates.append((row['counts']['nodes']-parent)/row['active_training_seconds'])
    # Fourth player is unmeasured at mature size. Penalize traversal2x and tools1.5x;
    # reserves multiply these scenarios again, never called measurements/bounds.
    active=10000000000/min(rates)*2
    def maximum(suffix):return max(x['wall_seconds'] for x in st if x['phase'].endswith(suffix))
    save=max(x['save_seconds'] for x in cp.values())
    load=max(x['stage_wall_seconds']-x['elapsed_seconds'] for x in cp.values())
    total_hands=8*4096*24*2
    largest_load=max(x['native_load_seconds'] for x in r['proofs'].values())
    play_rate=max(x['native_play_seconds']/(2*x['hands']) for x in r['proofs'].values())
    replay_rate=max(x['wall_seconds']/r['proofs'][x['phase'].removesuffix('-verify')]['hands'] for x in st if x['phase'].endswith('-verify'))
    components=[('active traversal',active,3*active),('two saves',2*save*1.5,2*2*save*1.5),
        ('one capped resume and startup',load*1.5+60,2*(load*1.5+60)),
        ('two average exports',2*maximum('-export')*1.5,4*maximum('-export')*1.5),
        ('two checkpoint audits',2*maximum('-audit')*1.5,4*maximum('-audit')*1.5),
        ('two binary conversions',2*maximum('-convert')*1.5,4*maximum('-convert')*1.5),
        ('two binary parity audits',2*maximum('-binary-audit')*1.5,4*maximum('-binary-audit')*1.5),
        ('two arena process startups',2*largest_load*1.5,4*largest_load*1.5),
        ('play and trace write including reproduction',2*total_hands*play_rate*4,6*total_hands*play_rate*4),
        ('initial-hand replay and pair validation',total_hands*replay_rate*4,2*total_hands*replay_rate*4),
        ('global summaries and tail readout',900,1800),('build and correctness qualification',900,1800),('report publication',1200,1800)]
    central=sum(x[1] for x in components);reserve=sum(x[2] for x in components);allowance=math.ceil(reserve/3600)*3600
    z=NormalDist().inv_cdf(1-.05/8);power=[]
    for sd in (200,400,800):
        se=sd/math.sqrt(4096)
        power.append(dict(assumed_block_sd_bb100=sd,se_bb100=se,approx_family_lower_distance=z*se,primary_true_gain10_power=NormalDist().cdf(10/se-z),neutral_script_clears_minus5_power=NormalDist().cdf(5/se-z)))
    # Two cp+two gzip+two binaries+mass, scenarios by observed retained sizes.
    # Binary files are metadata-described rows: reserve200bytes/key across derivatives.
    retained=2*250000000*200
    trace_bytes=2*total_hands*8192
    required=retained+trace_bytes+30*2**30
    return dict(status='proposal-not-main-admitted',source_input=INPUT,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        seed=2026102341001,players=4,stack_bb=100,targets=[3000000000,10000000000],entry_threshold=250000000,
        blocks_per_lineup=4096,lineups=8,permutations=24,initial_hands=total_hands,reproduction_hands=total_hands,
        family='one-sided95 Student-t/Bonferroni8; trained lower>0; seven fixed scripted/mixed paired lower>-5',
        components=[dict(name=n,central_seconds=c,reserved_seconds=u) for n,c,u in components],central_seconds=central,reserved_seconds=reserve,proposed_allocation_seconds=allowance,
        storage=dict(model_derivatives_scenario_bytes=retained,all_trace_scenario_bytes=trace_bytes,manual_headroom_bytes=30*2**30,requested_free_bytes=required),
        power_scenarios=power,limits='PR404 three-player200BB costs only; 2x traversal/1.5x tools/4x play and proof penalties plus reserves. Fourth-player mature runtime and block SD unknown. No saturation or completion guarantee; no automatic extension, no training/main launch.',
        qualification='Fresh tiny four-player100BB engineering only on bb128; M4 inaccessible; do not copy or depend on its fixture models.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(proposal(),f,indent=2);f.write('\n')


if __name__=='__main__':main()
