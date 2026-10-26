"""Create compact rows from the fixed pilot; never reruns a solver."""
import argparse,csv,json,statistics
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 d=json.loads(a.input.read_text());a.out.mkdir(parents=True,exist_ok=False)
 rows=[]
 for c in d['cases']:
  if c['status']!='supported':
   rows.append(dict(case=c['case'],pot_bb=c['pot_bb'],sweeps='',status='unsupported',nodes='',decision_ms=1000*statistics.median(c['decision_seconds']),range_ms='',prepare_ms='',solve_ms='',quality_ms='',exploitability_bb='',reference_1024_bb='',projection_tv='',reason=c['reason']))
  else:
   for r in c['records']:
    ts=r['native_timings'];median=lambda key:1000*statistics.median(t[key] for t in ts)
    rows.append(dict(case=c['case'],pot_bb=c['pot_bb'],sweeps=r['sweeps'],status='supported',nodes=c['nodes'],decision_ms=1000*statistics.median(r['complete_decision_seconds']),range_ms=median('likelihood_seconds')+median('projection_seconds'),prepare_ms=median('tree_and_solver_preparation_seconds'),solve_ms=median('solve_seconds'),quality_ms=median('quality_seconds'),exploitability_bb=r['quality']['exploitability_bb'],reference_1024_bb=c['reference_1024']['quality']['exploitability_bb'],projection_tv=c['law']['projection_total_variation'],reason=''))
 with (a.out/'measurements.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 lines=['| Case | Pot BB | Nodes | Sweeps | Complete ms | Ranges ms | Solve ms | Exploitability BB |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  if r['status']=='supported':lines.append('|{case}|{pot_bb:.2f}|{nodes}|{sweeps}|{decision_ms:.2f}|{range_ms:.2f}|{solve_ms:.2f}|{exploitability_bb:.6f}|'.format(**r))
  else:lines.append(f"|{r['case']}|{r['pot_bb']:.2f}|unsupported|—|{r['decision_ms']:.2f}|—|—|—|")
 (a.out/'table.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'status':d['status'],'supported_roots':d['supported_roots'],'model_load_seconds':d['loading']['roundtrip_startup_seconds'],'total_wall_seconds':d['total_wall_seconds']}))
if __name__=='__main__':main()
