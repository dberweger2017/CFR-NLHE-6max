"""Profile one `add` against a full reservoir with run 1's `seen` counts (production keep rate)."""
import cProfile, json, pstats, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from scripts import neural_deep_cfr as d
f, buf, cap = sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
if not (buf / 'advantage' / 'state.json').exists():
    d.main(['add', '--samples', f, '--advantage-buffer', str(buf / 'advantage'), '--strategy-buffer', str(buf / 'strategy'), '--capacity', str(cap), '--seed', '1'])
    for kind, seen in (('advantage', 913639602), ('strategy', 2661917069)):
        s = json.loads((buf / kind / 'state.json').read_text()); s['seen'] = seen; s['batches'] = 1374
        (buf / kind / 'state.json').write_text(json.dumps(s, indent=1) + '\n')
t = time.time()
cProfile.run("d.main(['add', '--samples', f, '--advantage-buffer', str(buf / 'advantage'), '--strategy-buffer', str(buf / 'strategy'), '--capacity', str(cap), '--seed', '20261110000001'])", '/tmp/add.prof')
print('add seconds', round(time.time() - t, 2))
pstats.Stats('/tmp/add.prof').sort_stats('tottime').print_stats(12)
