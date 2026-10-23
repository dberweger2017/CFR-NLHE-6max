"""Price and size the prospective200BB campaign using closed historical metadata only."""
from pathlib import Path
from statistics import NormalDist
import argparse
import csv,hashlib,json,math


def build_proposal():
    root=Path(__file__).resolve().parents[1];read=lambda name:json.loads((root/name).read_text())
    sizing_path='configs/research/nplayer-v06-acceptance-sizing.json';old=read(sizing_path)
    maturity=read('docs/reports/nplayer-bb200-maturity/campaign-proposal.json')
    prior=read('docs/reports/nplayer-v06-acceptance/results.json')
    convert_rows=list(csv.DictReader((root/'docs/reports/nplayer-v06-acceptance/costs.csv').open()))
    mapseed={'2026101935003':'2026102240001','202610200601':'2026102261001','202610200602':'2026102261002'}
    rows=[]
    for i,r in enumerate(old['rows']):
     historical={k:v for k,v in r.items() if k not in ('mean','se8192','planning_power')}
     rows.append({**historical,'historical_mean_bb100':r['mean'],'historical_se8192_bb100':r['se8192'],
      'historical_planning_power':r['planning_power'],'historical_seed':r['seed'],'seed':mapseed[str(r['seed'])],
      'historical_name':r['name'],'name':mapseed.get(str(r['name']),r['name']),
      'historical_blocks':r['blocks'],'blocks':4*r['blocks'],'root':20261022620001+i})
    assert len(rows)==30 and len({r['root'] for r in rows})==30
    blocks=sum(r['blocks']*r['cases'] for r in rows)
    assert blocks==4*old['case_blocks']==1757184
    z=NormalDist().inv_cdf(1-.05/30)
    scenarios=[]
    for name,effect,sd,neutral in [('historical-means-same-SD',1,1,False),('75pct-means-double-SD',.75,2,False),('half-means-double-SD',.5,2,False),('75pct-script-means-neutral-continuations-double-SD',.75,2,True)]:
     powers=[]
     for r in rows:
      mu=0 if neutral and r['gate']!='script-profit' else effect*r['historical_mean_bb100']
      se=r['historical_se8192_bb100']*sd*math.sqrt(8192/r['blocks'])
      powers.append(NormalDist().cdf((mu-r['margin'])/se-z))
     scenarios.append({'name':name,'effect_multiplier':effect,'SD_multiplier':sd,'neutral_continuations':neutral,
      'minimum_per_gate_power':min(powers),'conditional_family_union_lower_bound':max(0,1-sum(1-p for p in powers)),
      'illustrative_independence_all_pass':math.prod(powers),'gate_powers':powers})
    # Full prospective cost; scales from closed historical workloads, never200BBpayoffs.
    converter=max(float(r['wall_seconds']) for r in convert_rows if r['category']=='conversion')
    binaryaudit=max(float(r['wall_seconds']) for r in convert_rows if r['category']=='full-row audit')
    loads=prior['costs']['native_load_seconds'];play=prior['costs']['native_play_seconds_including_reproduction']
    native=prior['costs']['groups']['native evaluation']['wall_seconds'];other=native-loads-play
    replay=prior['costs']['groups']['replay and reconciliation']['wall_seconds'];readout=prior['costs']['groups']['global barrier/readout']['wall_seconds']
    parts=[{'name':'model training, saves, six exports and checkpoint audits','central_seconds':maturity['model_campaign_central_seconds'],'reserved_seconds':maturity['model_campaign_reserved_seconds'],'basis':'PR402 model campaign arithmetic unchanged'},
     {'name':'six binary conversions','central_seconds':6*converter,'reserved_seconds':12*converter,'basis':'six times slowestPR367 conversion;2xreserve'},
     {'name':'six full-row binary parity audits','central_seconds':6*binaryaudit,'reserved_seconds':12*binaryaudit,'basis':'six times slowestPR367 binary audit;2xreserve; separate from checkpoint/export audit'},
     {'name':'qualification and fixed fixtures','central_seconds':900,'reserved_seconds':1800,'basis':'explicit15/30min allowance, no new training-cost pilot'},
     {'name':'acceptance native processes including reproduction','central_seconds':1.25*loads+4*2*play+2*other,'reserved_seconds':2*1.25*loads+3*4*2*play+2*2*other,'basis':'same18policyloads at1.25x100BBload;4xcounts and2xplaycost per hand;2xload/other and3xplay reserve'},
     {'name':'independent replay and reconciliation','central_seconds':4*2*replay,'reserved_seconds':2*4*2*replay,'basis':'4xcounts,2xdepth/work cost scenario, then2xreserve'},
     {'name':'global barrier/readout','central_seconds':4*readout,'reserved_seconds':8*readout,'basis':'4xhistorical workload;2xreserve'},
     {'name':'analysis and report','central_seconds':1800,'reserved_seconds':2700,'basis':'explicit30/45min allowance'}]
    central=sum(p['central_seconds'] for p in parts);reserve=sum(p['reserved_seconds'] for p in parts)
    handbytes=2*blocks*6*8192
    binarybytes=14148446930*6
    modelbytes=maturity['model_storage_retained_bytes_rough']
    massbytes=83545787*16*6
    capacity={'raw_trace_bytes_scenario':handbytes,'trace_bytes_per_hand_scenario':8192,'model_checkpoint_and_average_bytes_scenario':modelbytes,'six_binary_derivative_bytes_scenario':binarybytes,'six_zero_mass_key_files_bytes_scenario':massbytes,'science_output_bytes_scenario':handbytes+binarybytes+modelbytes+massbytes,'headroom_bytes':30*2**30,'requested_free_nvme_bytes':360*2**30,'not_a_guaranteed_upper_bound':True,'cleanup_staging_upload_owner':'vacuum-cleaner agent; this campaign must not clean/move/upload','no_automatic_disk_guard':True}
    assert capacity['science_output_bytes_scenario']+capacity['headroom_bytes']<capacity['requested_free_nvme_bytes']
    proposal={'status':'proposal-not-admitted-no-main-launch','prior_result':'PR402','parent_checkpoint_sha256':'55d89c553ba1756eac1af117847b30e8b18e4f901afba942ee5a906bc00249ad','training_seeds':list(mapseed.values()),'targets':[3000000000,10000000000],'entry_freeze_threshold':250000000,'native_iteration_boundary_overshoot_allowed':True,'training_threads':16,'evaluation_threads':8,'no_further_training_cost_pilot':True,'family':'one-sided simultaneous95% Student-t/Bonferroni30, scripts/direct>0, cyclic>-5BB100','primary_unit':'independent six-seat-permutation deal block; reproduction not independent','case_blocks':blocks,'initial_hands':6*blocks,'reproduction_hands':6*blocks,'cases':36,'rows':rows,'power_scenarios':scenarios,'power_warning':'Normal-approximation conditional scenarios, not predictive assurance;100BB effects/variance do not establish200BB strength. Actual final intervals use Student-t and observed independent block variance. Gate dependence makes independence product illustrative only.','cost_components':parts,'central_seconds':central,'reserved_seconds':reserve,'proposed_allocation_seconds':18*3600,'not_an_elapsed_kill':True,'excluded_external_work':['owner vacuum-cleaner cleanup/staging/upload','release packaging/publication'],'runtime_assumptions':'Conditional scaling only; no200BBbinary/strength timings measured. No global cache flush. An observed correctness/resource failure is terminal; no automatic science retry/extra samples.','storage':capacity,'source_sha256s':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in [sizing_path,'docs/reports/nplayer-bb200-maturity/campaign-proposal.json','docs/reports/nplayer-v06-acceptance/results.json','docs/reports/nplayer-v06-acceptance/costs.csv']}}
    return proposal


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    proposal=build_proposal()
    with args.out.open('x') as stream:
        stream.write(json.dumps(proposal,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'central_hours':proposal['central_seconds']/3600,
        'reserved_hours':proposal['reserved_seconds']/3600,
        'initial_hands':proposal['initial_hands'],'rows':len(proposal['rows']),
        'powers':[{k:v for k,v in s.items() if k!='gate_powers'} for s in proposal['power_scenarios']],
        'outputs_GiB':proposal['storage']['science_output_bytes_scenario']/2**30},indent=2))


if __name__=='__main__':main()
