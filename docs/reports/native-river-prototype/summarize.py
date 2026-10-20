"""Reproduce the compact prepared-river CSV/table from the retained JSON."""
import csv
import json
from pathlib import Path
import statistics
import sys

source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
r=json.loads(source.read_text())
assert len(r['cases'])==12 and not r['source_worktree_dirty']
assert r['numerical_correctness']=='passed'
assert all(c['same_profile_gradient_average_value_and_br_parity'] for c in r['cases'])
assert all(c['leaf_evaluation_mode']=='sorted-linear' for c in r['cases'])
rows=[]
for c in r['cases']:
 assert [x['sweeps'] for x in c['records']]==[16,64,256]
 for x in c['records']:
  rows.append(dict(case=c['index'],holdings_per_seat=c['holdings'][0],nodes=c['nodes'],root_pot_bb=c['root_pot_bb'],sweeps=x['sweeps'],
    native_solve_ms=1000*statistics.median(x['native_solve_seconds']),
    preparation_ms=1000*statistics.median(x['preparation_seconds']),
    quality_ms=1000*statistics.median(x['quality_seconds']),
    compact_action_roundtrip_ms=1000*statistics.median(x['compact_action_roundtrip_seconds']),
    full_profile_roundtrip_ms=1000*statistics.median(x['roundtrip_seconds']),
    python_solve_ms=1000*x['python_solve_seconds'],solve_speedup=x['solve_speedup'],
    python_exploitability_bb=x['python_quality']['exploitability_bb'],native_exploitability_bb=x['native_quality']['exploitability_bb'],
    signed_quality_gap_bb=x['quality_signed_gap_bb'],quality_tolerance_bb=x['quality_tolerance_bb'],quality_agreement=x['quality_within_tolerance']))
with (out/'measurements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
lines=['| Sweeps | Native solve ms, range | Prepared compact roundtrip ms, range | Median solver speedup |','|---|---:|---:|---:|']
for n in (16,64,256):
 a=[x for x in rows if x['holdings_per_seat']==1081 and x['sweeps']==n]
 def span(key):return f"{min(x[key] for x in a):.2f}–{max(x[key] for x in a):.2f}"
 lines.append(f"| {n} | {span('native_solve_ms')} | {span('compact_action_roundtrip_ms')} | {statistics.median(x['solve_speedup'] for x in a):.2f}× |")
(out/'timing-table.md').write_text('\n'.join(lines)+'\n')
