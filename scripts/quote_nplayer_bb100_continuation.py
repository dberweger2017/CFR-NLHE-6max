"""Informational main-run forecast from mature PR352 costs, not a runtime guard."""
import argparse
import json
from pathlib import Path

from scripts.nplayer_bb100_continuation import TARGET, SOURCE, prior, cases
from scripts.nplayer_overnight import load

BASELINE_ZERO_ROWS = 79_729_265
POST_FREEZE_NODES_PER_SECOND = 4_830_005.973934204


def quote(qualification):
    q=load(qualification)
    if q['status']!='passed' or not q['fixture']:
        raise ValueError('completed fixture qualification required')
    r=load(SOURCE/'docs/reports/nplayer-pruning-strength/results.json')
    if r['status']!='settled':raise ValueError('historical mature profile not settled')
    c=r['costs'];stages=c['original_attempt_stages']
    # This is a planning model. Explicitly keep assumptions separate from measured costs.
    active=(TARGET-prior.BASELINE_NODES)/POST_FREEZE_NODES_PER_SECOND
    one_endpoint=(c['training_stages_wall_seconds']-c['pruned_3b_active_seconds'])/2
    load_seconds=425.*1.15  # measured two-policy load425s; mass-tag traversal allowance15%.
    components=dict(active_training=active, one_endpoint_processing=one_endpoint,
        checkpoint_reload=400., two_full_audits_with_metadata=2*stages['audit-nodes']['wall_seconds']*1.3,
        two_policy_load_and_mass_tags=load_seconds, native_nonload_and_replay=300.,
        final_hashes_lookup_checks_readout=180.)
    hands=sum(c['blocks']*6 for c in cases())
    trace_bytes=q['evaluation_cost']['trace_bytes']*hands/q['fixture_hands']
    # Candidate zero membership cannot increase under this unchanged nonnegative cumulative average.
    mass_bytes=BASELINE_ZERO_ROWS*16*2
    checkpoint_bytes=9_712_092_292
    policy_bytes=5_600_275_976
    disk=checkpoint_bytes+policy_bytes+mass_bytes+trace_bytes
    return dict(scope='prospective single-seed continuation; not a measured full-job ETA or kill budget',
        active_training_seconds=active,components_seconds=components,
        estimate_seconds=sum(components.values()),planning_allowance_seconds=sum(components.values())*1.25,
        predicted_output_bytes=disk,predicted_trace_bytes=trace_bytes,mass_metadata_upper_bytes=mass_bytes,
        observed_historical_two_model_rss_gib=66.03,inference_row_size_increase_bytes=0,
        initial_hands=hands,reproduction_hands=hands,
        assumptions=['one endpoint uses half of historical two-endpoint nontraining overhead; cadence differs',
                     'checkpoint reload400s and native/replay/readout allowances are estimates',
                     'audits add30% and model loading15% for mass metadata; not a mature benchmark',
                     'trace bytes scale small qualification traces; reached paths may differ at3B/10B',
                     'disk/swap remain manual observations; forecast never stops a running job'],
        historical_source='docs/reports/nplayer-pruning-strength/results.json',qualification=str(qualification))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('qualification',type=Path)
    a=p.parse_args();print(json.dumps(quote(a.qualification),indent=2))
