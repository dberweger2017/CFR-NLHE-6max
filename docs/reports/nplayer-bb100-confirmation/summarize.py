"""Build the compact PR357 report from already settled, verified remote readouts.

Does not replay hands, fit intervals, select endpoints or run any science.
Inputs are the compact evidence/cost retrieval described in results.md.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

SEEDS = (202610200601, 202610200602)
STREETS = ('preflop', 'flop', 'turn', 'river')


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n');w.writeheader();w.writerows(rows)


def summarize(evidence, detail, out):
    x = json.loads(evidence.read_text());d = json.loads(detail.read_text())
    f = x['files'];r = f['results.json'];proof = f['evaluation-verified.json']
    assert f['status.json']['status'] == 'complete' and r['status'] == 'settled'
    assert proof['status'] == 'passed'
    assert proof['initial_hands'] == proof['reproduction_hands'] == 2064384
    assert r['initial_hands'] == r['reproduction_hands'] == 2064384
    stages = {k.split('/')[1]:v for k,v in f.items() if k.startswith('measurements/')}
    assert len(stages) == 18 and all(v['returncode'] == 0 for v in stages.values())
    strength=[];seats=[];lookups=[];endpoints=[];training=[];masses=[];diagnostics={}
    for row in r['rows'] + r['cross']:
        group = row.get('group', 'cross');s = row['score']
        assert s['family'] == (2 if group == 'direct' else 3 if group == 'cross' else 16)
        assert s['lower_family95'] <= s['mean_bb100'] <= s['upper_family95']
        margin = 0 if group == 'direct' else -5 if group == 'cross' else -50
        strength.append(dict(seed=row['seed'],group=group,opponent=row.get('opponent') or row.get('opponent_seed') or 'own-3B',
            **s,lower_margin=margin,passes_bound=s['lower_family95']>margin))
    assert sum(v['group']=='direct' for v in strength) == 2
    assert len(strength) == 21
    manifests = [(f'lineage-{seed}/comparison/evaluation-manifest.json',18) for seed in SEEDS]+[('cross/evaluation-manifest.json',6)]
    cases=[]
    for path,n in manifests:
        folder=path.rsplit('/',1)[0];m=f[path];p=f[folder+'/evaluation-verified.json']
        assert p['status']=='passed' and p['cases']==n and len(m['cases'])==n
        assert p['manifest_sha256']==x['sha256'][path]
        assert (proof['cross_manifest_sha256'] if n==6 else proof['manifests'][path])==x['sha256'][path]
        for c in m['cases']:
            name=folder+'/evaluation/'+c['name'];a=f[name+'/result.json'];b=f[name+'/replay.json']
            assert a['case']==c and a['status']==b['status']=='passed'
            assert a['hands']==b['hands']==c['blocks']*6==49152
            assert a['trace_sha256']==b['trace_sha256']
            if 'coverage' in a:
                assert a['coverage'][0]['trace_sha256']==a['coverage'][1]['trace_sha256']==a['trace_sha256']
            cases.append(dict(folder=folder,case=c,trace_sha256=a['trace_sha256'],replay=b,
                coverage=a.get('coverage')))
    assert len(cases)==42
    for seed in SEEDS:
        line=r['lineages'][str(seed)];models=line['models'];base=None
        for alias,target in (('baseline',3000000000),('candidate',10000000000)):
            ep=f[f'lineage-{seed}/{alias}-endpoint.json'];cp=ep['checkpoint']
            mass=f[f'lineage-{seed}/{alias}-mass/receipt.json'];stage=stages[f'{seed}-train-{alias}']
            assert target<=cp['nodes']<target+1000000 and cp['entries']>=250000000
            assert mass['status']=='passed' and mass['rows']==mass['average_rows']==cp['entries']
            assert mass['checkpoint_sha256']==cp['sha256']==ep['model']['checkpoint_sha256']
            assert mass['policy_sha256']==ep['model']['sha256']==models[alias]['sha256']
            assert mass['keyset_sha256']==cp['keyset_sha256']
            if base is None:base=cp
            else:assert all(cp[k]==base[k] for k in ('entries','frozen_at','keyset_sha256'))
            endpoints.append(dict(seed=seed,alias=alias,checkpoint=cp,model=ep['model']))
            masses.append(dict(seed=seed,alias=alias,**mass))
            events=stage['events'];active=next(e['active_seconds'] for e in events if e['event']=='complete')
            export=next(e['export_seconds'] for e in events if e['event']=='exported')
            previous=0 if alias=='baseline' else base['nodes']
            phase=d['phase_samples'][f'{seed}-train-{alias}'].get('load')
            training.append(dict(seed=seed,alias=alias,nodes=cp['nodes'],iterations=cp['iteration'],entries=cp['entries'],
                additional_nodes=cp['nodes']-previous,active_seconds=active,nodes_per_second=(cp['nodes']-previous)/active,
                save_seconds=cp['save_seconds'],export_seconds=export,
                sampled_load_span_seconds=phase['last']-phase['first'] if phase else 0,
                wall_seconds=stage['wall_seconds'],cpu_seconds=stage['cpu_seconds'],
                sampled_peak_rss_bytes=x['resources'][f'{seed}-train-{alias}']['peak_rss_bytes']))
        for row in line['rows']:
            for dimension in ('by_seat','by_position'):
                for alias,values in row[dimension].items():
                    for index,score in enumerate(values):
                        seats.append(dict(seed=seed,group=row['group'],opponent=row['opponent'] or 'own-3B',dimension=dimension,alias=alias,index=index,**score))
        diagnostics[str(seed)]={}
        for name,v in line['diagnostics'].items():
            diagnostics[str(seed)][name]={k:val for k,val in v.items() if k!='singleton_paths'}
            counts=v['singleton_lookup_by_position_street']
            for pos in range(3):
                for street in range(4):
                    for policy,alias in enumerate(('baseline','candidate')):
                        a=counts[pos][street][policy]
                        lookups.append(dict(seed=seed,case=name,position=pos,street=STREETS[street],probed_policy=alias,
                            positive_mass=a[0],zero_mass=a[1],missing=a[2],decisions=sum(a)))
    costs={name:{k:v[k] for k in ('returncode','wall_seconds','cpu_seconds','sampled_peak_rss_by_phase')} for name,v in stages.items()}
    whole=f['status.json']['at']-f['launch.json']['at']
    totals=dict(wall_seconds=whole,child_cpu_seconds=sum(v['cpu_seconds'] for v in stages.values()),
        active_training_seconds=sum(v['active_seconds'] for v in training),save_seconds=sum(v['save_seconds'] for v in training),
        export_seconds=sum(v['export_seconds'] for v in training),
        peak_rss_bytes=max(v['peak_rss_bytes'] for v in x['resources'].values()),
        max_cpu_c=max(v['max_temperatures_c']['Package id 0'] for v in x['resources'].values()),
        max_thermistor15_c=max(v['max_temperatures_c']['Thermistor 15'] for v in x['resources'].values()),
        staged_files=len(x['relocations']),staged_bytes=sum(v['bytes'] for v in x['relocations']))
    compact=dict(status='settled',root=x['root'],launch=f['launch.json'],completed=f['status.json'],proof=proof,
        repeated_primary_gain=r['repeated_primary_gain'],scripted_safeguard=r['scripted_safeguard'],cross_seed_safeguard=r['cross_seed_safeguard'],
        strength=strength,absolute_returns={seed:[{k:v for k,v in row.items() if k!='score'} for row in lineage['rows']] for seed,lineage in r['lineages'].items()},endpoints=endpoints,mass_audits=masses,case_proofs=cases,diagnostics=diagnostics,
        training=training,costs=costs,totals=totals,evaluation_costs=d['evaluation_costs'],resources=x['resources'],
        relocations=x['relocations'],source_file_sha256=x['sha256'],
        retrieval_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (evidence,detail)},
        provenance_note='Remote final reader rehashed every initial/reproduction trace and replay proof before settled readout; local summary verifies compact proof/count/model/family consistency without rerunning science.')
    out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(compact,indent=2)+'\n')
    write_csv(out/'strength.csv',strength);write_csv(out/'training.csv',training)
    write_csv(out/'seats-and-positions.csv',seats);write_csv(out/'lookup-counts.csv',lookups)
    report=['# Independent 100 BB seed confirmation — results','',
        'Both fresh 3B→10B primary gains repeat, and every cyclic cross-seed safeguard passes. The scripted safeguard fails: random and random+TAG regress on both fresh seeds after family adjustment. Keep 10B as a conditional research candidate and retain 3B; this is not universal-strength or release qualification.','',
        '## Verified design and decision','',
        'Two fresh unpruned three-player 100 BB/K50 lineages, seeds 202610200601/02, each 0→3B→10B with its own fixed nominal 250M-key membership. Same float64 average, menu/key schema, fast 8 roots/seat and 16 threads as PR355. Original seed 2026101935003 is discovery evidence and a cyclic reference, not a third fresh primary.','',
        'All 42 cases (8192 independent six-hand blocks each) passed independent initial replay and byte-identical reproduction: **2,064,384 initial +2,064,384 reproduced hands**. All four full row/export audits and all 18 stage return codes pass. No final scientific retry, guard stop or endpoint extension occurred. Reproductions and seat permutations do not add independent samples.','',
        'Primary statistic is the **mean oriented singleton contrast**: half the difference between reciprocal singleton returns, not pooled player return or a heads-up win rate. Script/cyclic contrasts are full singleton return differences. Predeclared simultaneous family 95% intervals use Bonferroni 2/16/3 respectively; no nested historical family 8 flags are used.','',
        '| Seed | Panel | 10B−3B BB/100 | Family 95% interval | Declared lower-bound test |','|---|---|---:|---|---|']
    for v in strength:
        report.append(f"| {v['seed']} | {v['opponent']} | {v['mean_bb100']:+.2f} | [{v['lower_family95']:+.2f}, {v['upper_family95']:+.2f}] | {'Pass' if v['passes_bound'] else 'Unresolved'} >{v['lower_margin']} |")
    report += ['', '**Repeated primary gain: pass. Cyclic safeguard: pass (all 3). Script/mixed safeguard: fail (11/16 bounds pass).** Five unresolved −50 bounds are seed 601 random/check-call/random+TAG and seed 602 random/random+TAG. Both random and random+TAG intervals lie below zero on both fresh seeds: these are demonstrated panel regressions. None of their family95 upper bounds is below −50; a loss beyond that tolerance is not established at the declared simultaneous level. Check-call does not show consistent direction across seeds.','',
        'Both fresh own-3B improvements are established. Two cyclic gains clear zero after adjustment; the third is inconclusive for improvement but clears the −5 safeguard. Meaningful adverse scripted evidence remains. They do not demonstrate multiplayer Nash convergence, explain the causal mechanism, establish that search will fix the losses, or justify default/release adoption. Three fixed seeds including discovery are still a small training population; the cyclic panel is not a full population tournament.','',
        '## Absolute returns, positions and lookup diagnostics','',
        '| Fresh seed | Field | 3B absolute BB/100 | 10B absolute BB/100 |','|---|---|---:|---:|']
    for seed in SEEDS:
        for v in r['lineages'][str(seed)]['rows']:
            if v['group']!='direct':report.append(f"| {seed} | {v['opponent']} | {v['baseline_absolute']['mean_bb100']:+.2f} | {v['candidate_absolute']['mean_bb100']:+.2f} |")
    report += ['', '[seats-and-positions.csv](seats-and-positions.csv) contains every within-seed absolute return and ordinary 95% interval by physical seat and button-relative position (0=button,1=small blind,2=big blind). These are descriptive strata, not additional adjusted primary tests. Direct 10B singleton returns by button/SB/BB are '+ '; '.join(str(seed)+': '+', '.join(f"{v['mean_bb100']:+.2f}" for v in r['lineages'][str(seed)]['rows'][0]['by_position']['candidate']) for seed in SEEDS)+ ' BB/100.','',
        '[lookup-counts.csv](lookup-counts.csv) retains singleton decision counts by case, position, street and **both probed policies at the same reached state**. Status order is positive original average mass / represented zero mass / missing; do not interpret two probes as two independent decisions. Compact JSON retains matched transitions, reached-street/pot-band counts, river eligibility and own-missing cross coverage. Cross tables can differ; represented cross rows cannot be labeled positive mass without matching metadata. Cross per-seat payoff intervals were not precomputed and are not invented here.','',
        '| Seed | Endpoint | Positive-mass rows | Zero-mass rows | Missing singleton probes / all probes |','|---|---|---:|---:|---:|']
    for seed in SEEDS:
        for alias in ('baseline','candidate'):
            m=next(v for v in masses if v['seed']==seed and v['alias']==alias)
            v=[a for a in lookups if a['seed']==seed and a['probed_policy']==alias]
            report.append(f"| {seed} | {alias} | {m['positive_mass_rows']:,} | {m['zero_mass_rows']:,} | {sum(a['missing'] for a in v):,} / {sum(a['decisions'] for a in v):,} |")
    report += ['', 'Lookup fractions depend on the evaluated field and reached paths. Lower zero-mass coverage or different pot/river distributions are descriptive associations; they do not establish why returns changed. Exact path examples remain in the retained settled raw readout, rather than selecting a few large losing pots as a causal explanation.','',
        '## Actual training and end-to-end costs','',
        '| Seed | Segment | Nodes reached | Iterations | Active s | Mnodes/s | Save s | Export s | Stage wall s | Child CPU s | Peak GiB |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in training:
        report.append(f"| {v['seed']} | {'0→3B' if v['alias']=='baseline' else '3B→10B'} | {v['nodes']:,} | {v['iterations']:,} | {v['active_seconds']:.2f} | {v['nodes_per_second']/1e6:.3f} | {v['save_seconds']:.2f} | {v['export_seconds']:.2f} | {v['wall_seconds']:.2f} | {v['cpu_seconds']:.2f} | {v['sampled_peak_rss_bytes']/2**30:.2f} |")
    report += ['', f"Whole campaign: **{whole/3600:.3f}h wall, {totals['child_cpu_seconds']/3600:.3f} child CPU-hours**; active traversal {totals['active_training_seconds']/60:.2f}min. Sampled peak family RSS **{totals['peak_rss_bytes']/2**30:.2f}GiB**; max sampled CPU **{totals['max_cpu_c']:g}°C**, Thermistor 15 **{totals['max_thermistor15_c']:g}°C**, below unchanged 90/100°C stops. Launch/finish were {datetime.fromtimestamp(f['launch.json']['at'],timezone.utc).isoformat()} / {datetime.fromtimestamp(f['status.json']['at'],timezone.utc).isoformat()} (MadridUTC+2).",'',
        'Active traversal excludes checkpoint I/O and is distinct from phase wall time. Continuation checkpoint-load sample spans were '+', '.join(f"{v['sampled_load_span_seconds']:.2f}s" for v in training if v['alias']=='candidate')+' (first-to-last samples, approximate). Stage wall also includes launch, hash/verification, export, accounting and monitoring overhead; save/export counters are native event timings and do not partition total wall exactly. All segments use the same 16-thread recipe; no historical production-writer allocation is used for a speed claim.','',
        '| Evaluation | Policy loads | Native load s | Native play s incl. reproduction | Replay wall s | Stage wall s |','|---|---:|---:|---:|---:|---:|']
    for key,v in d['evaluation_costs'].items():
        name='cross-evaluation' if key.startswith('cross/') else key.split('/')[0].replace('lineage-','')+'-evaluation'
        report.append(f"| {name} | {v['policy_loads']} | {v['native_load_seconds']:.2f} | {v['native_play_seconds']:.2f} | {v['replay_wall_seconds']:.2f} | {stages[name]['wall_seconds']:.2f} |")
    report += ['', f"Four audits: {sum(v['wall_seconds'] for k,v in stages.items() if '-audit-' in k)/60:.2f}min wall. Verified staging: {sum(v['wall_seconds'] for k,v in stages.items() if '-stage-' in k)/60:.2f}min. Final statistical readout/revalidation: {stages['global-readout']['wall_seconds']:.2f}s. Full per-stage costs and sampled phase RSS are in the compact JSON. CPU sums are child user+system time, not host electricity; one host, two fresh fixed seeds, sequential order and sampled RSS/temperatures limit generalization.", '',
        'Repeated inference loading is the clearest engineering cost: the cross panel spends 2656.51 s loading versus 5.72 s in native play. Cheaper exact inference loading remains a separate proposed work package; no loader or river-search implementation was tested by this study.','',
        '## Provenance, retention and reproduction','',
        'Frozen upstream `edd5bc767bdeea6bc41e695bbe2cc0f089042f62`; standalone source-v3 snapshot `312a33b6f99977c618b19ba00fafe1ab015b4001`, 700 matching source/config hashes. Config `6d15cb8b9630eb0e22665d50cd35de68aa2f3dd7b3e0614d5093fa5372b523b0`. Exact binaries/qualification are pinned in [launch.json](launch.json). Four endpoint checkpoint/export/keyset hashes and all 42 replay/manifests are recorded in [results.json](results.json). Both within-lineage keysets match; between-seed sets differ as expected.','',
        'The earlier miniature fixture readout-phase error and setup clone/import failures remain preserved; the corrected fresh qualification passed 47 focused tests, 216 real K50 diagnostic hands / 120 legacy parity hands, and 504 initial + 504 reproduction full-fixture hands before the main attempt. No final main failure was discarded or retried.','',
        f"Owner-approved staging verified **{totals['staged_files']} new files / {totals['staged_bytes']:,} bytes** in `/mnt/data2tb/research-cloud/PR-357-nplayer-bb100-seed-confirmation/main-v1/`, preserving accessible original paths with symlinks. Every relocation SHA256/path/size/mtime is in results.json and the remote relocations.jsonl. Existing PR350/355 inputs remain protected. Other controls, cross traces and source roots stay at their original NVMe paths. **Research-Cloud ZIP/Drive upload acceptance remains pending; nothing was deleted.**",'',
        'Compact evidence retrieval is stored locally under ignored `results/pr357-completed-20261020T0449/`. `evidence.json` contains only settled results, configs/endpoints/audit/proof/cost JSON, resource maxima and relocation receipts; `cost-detail-v2.json` contains evaluation-cost JSON and sampled load spans. Their SHA256 values are in results.json. The first cost-only retrieval had a shell-quoting NameError, before writing any remote state; its empty local output is retained. No models or raw hand/resource traces were downloaded.','',
        'To reproduce the compact aggregation after retrieving those JSON receipts:','',
        '```sh','python3.11 docs/reports/nplayer-bb100-confirmation/summarize.py \\', '  results/pr357-completed-20261020T0449/evidence.json \\', '  results/pr357-completed-20261020T0449/cost-detail-v2.json \\', '  --out FRESH_REPORT_DIRECTORY','```','',
        'Restore an exact model/trace member from its recorded HDD destination with `rsync -a bb128:EXACT_RECORDED_DESTINATION FRESH_IGNORED_DIRECTORY/`, then verify the indexed SHA256. Nonstaged controls remain under the exact main root above; use `scp bb128:EXACT_CONTROL_PATH FRESH_IGNORED_DIRECTORY/`. Drive fallback is pending, not an accepted archive. See [RESULTS_INDEX](../../../RESULTS_INDEX.md).','',
        'Recommendation: retain 10B as the leading research candidate for trained-opponent play, keep 3B and all adverse panels, and address inference loading before repeating large evaluation campaigns. Primary gain repeats, but the predeclared overall safeguard combination does not pass. Adoption/release, more nodes, compact-key recipes and search remain separate owner decisions.']
    (out/'results.md').write_text('\n'.join(report)+'\n')
    print(json.dumps(totals,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('evidence',type=Path);p.add_argument('detail',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();summarize(a.evidence,a.detail,a.out)
