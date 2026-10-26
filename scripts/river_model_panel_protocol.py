"""Fixed PR436 scope, bit-preserving evidence comparisons and cost admission."""
import hashlib
import json
import math
import struct

PREFLIGHT = {'current': (0, 5, 10, 15, 24, 29, 34, 47), 'baseline': (0, 12, 24, 44)}
MAIN = {'current': tuple(range(48)), 'baseline': tuple(range(0, 48, 4))}
BASELINE = 'e6ae0bec74159e7c81ba65f48da6e9b3903c9b80'
PANEL_SHA = '9394fad0bba108f75cf6fbcb7955d259598b2da919711dadf0a753618098eb76'
SEED = 2026102643601


def bits(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('nonfinite evidence')
        return {'float64_bits': struct.pack('>d', value).hex()}
    if isinstance(value, list):
        return [bits(v) for v in value]
    if isinstance(value, dict):
        return {k: bits(v) for k, v in sorted(value.items())}
    return value


def deterministic(response):
    """Omit only declared timing paths and the session transport handle."""
    if response is None:
        return None
    x = json.loads(json.dumps(response, allow_nan=False))
    x.pop('worker_seconds_before_serialization', None)
    r = x.get('result', {})
    r.pop('timings', None)
    for checkpoint in r.get('checkpoints', []):
        checkpoint.pop('elapsed_seconds', None)
    for key in ('traversal_seconds', 'update_seconds', 'fold_leaf_seconds',
                'showdown_leaf_seconds', 'traversal_excluding_leaves_seconds'):
        r.get('solver_timing', {}).pop(key, None)
    r.get('session', {}).pop('handle', None)
    return bits(x)


def signature(response):
    return hashlib.sha256(json.dumps(deterministic(response), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def reentry_matches(begin, again):
    a, b = begin['result'], again['result']
    session = a['session']
    expected = {k: a[k] for k in ('actions', 'probabilities')}
    expected.update(installed_search=session['installed_search'], fallback_reason=session['fallback_reason'],
                    profile_sha256=session['binding']['profile_sha256'], solver_advances=0)
    if again['status'] != 'ok' or json.dumps(bits({k:b.get(k) for k in expected}),sort_keys=True) != json.dumps(bits(expected),sort_keys=True):
        raise ValueError('same-root re-entry changes strategy/binding or advances solver')
    if b.get('off_tree_entry') is not None:
        raise ValueError('same-root re-entry became off-tree')


def first_actor(response):
    if response['status'] != 'ok':
        return deterministic(response)
    r = response['result']
    keys = ('actions', 'probabilities', 'produced_root_strategy', 'quality', 'sweeps',
            'requested_sweeps', 'algorithm', 'target_bb', 'nodes', 'holdings', 'law',
            'coverage', 'lookup_tag', 'search_menu')
    out = {k:r.get(k) for k in keys}
    s = r['session']
    out['session'] = {k:s[k] for k in ('installed_search', 'fallback_reason')}
    out['binding'] = s['binding']
    out['checkpoint_work'] = [{k:v for k,v in c.items() if k != 'elapsed_seconds'} for c in r.get('checkpoints', [])]
    return json.dumps(bits(out),sort_keys=True)


def verify_batch_pair(a, b, ids):
    for rows in (a['roots'], b['roots']):
        if [r['id'] for r in rows] != list(ids):
            raise ValueError('root inventory missing, duplicated or reordered')
    for one, two in zip(a['roots'], b['roots']):
        for key in ('begin', 'reentry', 'release'):
            if signature(one[key]) != signature(two[key]):
                raise ValueError(f'reproduction mismatch root{one["id"]}/{key}')
    return dict(roots=len(ids), float64_bits_and_profiles=True, no_exclusions=True)


def quote(batches, already_spent, available, forecast_memory):
    rate = {}; worst = {}; startup = 0.
    for version in ('current', 'baseline'):
        selected = [b for b in batches if b['version'] == version]
        if len(selected) != 2:
            raise ValueError('preflight requires two passes of both versions')
        for b in selected:
            if [r['id'] for r in b['roots']] != list(PREFLIGHT[version]):
                raise ValueError('preflight inventory differs')
        times = [r['begin_seconds'] for b in selected for r in b['roots']]
        overhead = [r['reentry_seconds']+r['release_seconds'] for b in selected for r in b['roots']]
        complete = [t+o for t,o in zip(times,overhead)]
        if not complete or any(not math.isfinite(t) or t < 0 for t in complete):
            raise ValueError('invalid measured cost')
        rate[version] = sum(complete)/len(complete)
        worst[version] = max(complete)
        startup += sum(b['startup_wall_seconds']+b['shutdown_seconds'] for b in selected)
    central = already_spent+startup+96*rate['current']+24*rate['baseline']+240
    reserved = already_spent+2*startup+4*(96*worst['current']+24*worst['baseline'])+600
    memory_ok = forecast_memory <= 6*2**30 and forecast_memory+2**30 <= available
    return dict(central_seconds=central, reserved_seconds=reserved, allowance_seconds=3600,
                already_spent_seconds=already_spent, full_panel_startup_seconds=startup,
                mean_complete_seconds=rate, max_complete_seconds=worst,
                forecast_family_bytes=forecast_memory, available_bytes=available,
                main_admitted=reserved <= 3600 and memory_ok,
                memory_admitted=memory_ok, no_outcomes_used=True, no_main_started=True,
                method='actual spent +2x startup +4x max per-version complete latency for96current/24baseline +600s proof/report; scenario not bound')
